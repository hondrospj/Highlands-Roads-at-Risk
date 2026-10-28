#!/usr/bin/env python3
"""Refresh the existing Sea Bright daily-peak inputs; retain terrain and model settings."""
import argparse,copy,hashlib,json,math,time,urllib.request
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo("America/New_York")

def iso(value): return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)
def stamp(value): return value.isoformat().replace("+00:00","Z")
def validate_stats(stats):
    assert stats["schema"]=="roads-at-risk-flood-stats-v2"
    station=stats["station"]
    assert station["usgsGaugeId"]=="01407600" and station["usgsParameterCode"]=="72279"
    assert station["noaaGaugeId"]==station["petssGaugeId"]=="8531804" and station["datum"]=="NAVD88"
    assert stats["datum"]=={"navd88OffsetFromMllwFt":-2.13,"mllwOffsetFromNavd88Ft":2.13}
    assert stats["thresholds"]["navd88"]=={"minor":3.07,"moderate":4.07,"major":5.07}
    assert stats["thresholds"]["mllw"]=={"minor":5.2,"moderate":6.2,"major":7.2}

def parse_response(payload,now):
    records=[]
    for series in payload.get("value",{}).get("timeSeries",[]):
        assert any(s.get("value")=="01407600" for s in series["sourceInfo"]["siteCode"]),"Unexpected USGS site"
        assert any(v.get("value")=="72279" for v in series["variable"]["variableCode"]),"Unexpected USGS parameter"
        assert series["variable"]["unit"]["unitCode"].lower() in ("ft","feet"),"Unexpected observation units"
        missing=float(series["variable"].get("noDataValue",-999999))
        for group in series.get("values",[]):
            for row in group.get("value",[]):
                try: value=float(row["value"]); instant=iso(row["dateTime"])
                except (ValueError,KeyError):continue
                if not math.isfinite(value) or value==missing:continue
                assert abs(value)<100 and instant<=now+timedelta(minutes=15),"Invalid stage/time"
                records.append((instant,value))
    assert records,"No actual USGS observations returned"
    return records

def merge(stats,records,now,receipts):
    validate_stats(stats);out=copy.deepcopy(stats);last=stats["archive"]["endDate"]
    days={r["date"]:dict(r) for r in stats["dailyPeakArchive"]};peaks={}
    for instant,value in records:
        date=instant.astimezone(TZ).date().isoformat()
        if date>=last:peaks[date]=max(peaks.get(date,-math.inf),value)
    assert peaks,"No observations for incremental archive window"
    thresholds=stats["thresholds"]["navd88"]
    for date,peak in peaks.items():
        # A previously stored partial day can only gain its later measured maximum.
        peak=round(max(peak,days.get(date,{}).get("peakNavd88Ft",-math.inf)),2)
        classification=next((k for k in ("major","moderate","minor") if peak>=thresholds[k]),"none")
        days[date]={"date":date,"peakNavd88Ft":peak,"peakMllwFt":round(peak+2.13,2),"classification":classification}
    rows=[days[k] for k in sorted(days)];latest=max(t for t,v in records)
    assert timedelta(minutes=-15)<=now-latest<=timedelta(hours=6),"USGS observation feed is stale"
    out["dailyPeakArchive"]=rows;out["dailyPeakNavd88Ft"]=sorted(r["peakNavd88Ft"] for r in rows)
    out["archive"].update(startDate=rows[0]["date"],endDate=rows[-1]["date"],days=len(rows),years=round(len(rows)/365.25,2),classificationCounts={k:sum(r["classification"]==k for r in rows) for k in ("none","minor","moderate","major")})
    out["generatedAt"]=stamp(now)
    out["sourceFreshness"]={"checkedAtUtc":stamp(now),"latestObservationUtc":stamp(latest),"source":"USGS NWIS instantaneous values","usgsGaugeId":"01407600","parameterCd":"72279","datum":"NAVD88","units":"ft","responseDigests":receipts,"incrementalFromLocalDate":last}
    for key in ("station","datum","thresholds","tideModel","verticalUncertaintyFt","topEvents"):
        assert out[key]==stats[key],"Static model setting changed: "+key
    assert all(days[r["date"]]==r for r in stats["dailyPeakArchive"] if r["date"]<last),"Historical archive was rewritten"
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument("--file",default="flood_stats.json");args=p.parse_args();path=Path(args.file);stats=json.loads(path.read_text());validate_stats(stats)
    now=datetime.now(timezone.utc);start=datetime.combine(datetime.fromisoformat(stats["archive"]["endDate"]).date(),datetime.min.time(),tzinfo=TZ).astimezone(timezone.utc);records=[];receipts=[]
    while start<now:
        end=min(start+timedelta(days=30),now)
        url="https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01407600&parameterCd=72279&startDT="+stamp(start)+"&endDT="+stamp(end)+"&siteStatus=all"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ShorelySafe-Highlands-refresh"}),timeout=90) as response:raw=response.read(16777217)
                assert len(raw)<=16777216,"Unexpectedly large USGS response";break
            except Exception:
                if attempt==2:raise
                time.sleep(2**attempt)
        records.extend(parse_response(json.loads(raw),now));receipts.append({"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)});start=end
    out=merge(stats,records,now,receipts);path.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out["sourceFreshness"]))
if __name__=="__main__":main()
