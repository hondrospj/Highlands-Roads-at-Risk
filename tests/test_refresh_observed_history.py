import copy,sys,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from refresh_observed_history import merge,validate_stats

def baseline():
 return {'schema':'roads-at-risk-flood-stats-v2','station':{'usgsGaugeId':'01407600','usgsParameterCode':'72279','noaaGaugeId':'8531804','petssGaugeId':'8531804','datum':'NAVD88'},'datum':{'navd88OffsetFromMllwFt':-2.13,'mllwOffsetFromNavd88Ft':2.13},'thresholds':{'navd88':{'minor':3.07,'moderate':4.07,'major':5.07},'mllw':{'minor':5.2,'moderate':6.2,'major':7.2}},'tideModel':{'trendFtPerYear':0.00321088},'verticalUncertaintyFt':0.5,'topEvents':[{'date':'1821-09-03','heightNavd88Ft':12}],'archive':{'startDate':'2026-10-26','endDate':'2026-10-27','days':2},'dailyPeakArchive':[{'date':'2026-10-26','peakNavd88Ft':2,'peakMllwFt':4.13,'classification':'none'},{'date':'2026-10-27','peakNavd88Ft':2.5,'peakMllwFt':4.63,'classification':'none'}]}
class ObservedHistoryTests(unittest.TestCase):
 def test_partial_day_completed_new_day_added_and_model_unchanged(self):
  s=baseline();now=datetime(2026,10,28,12,tzinfo=timezone.utc);out=merge(s,[(now-timedelta(hours=10),3.2),(now,4.2)],now,[])
  self.assertEqual(out['dailyPeakArchive'][0],s['dailyPeakArchive'][0]);self.assertEqual(out['dailyPeakArchive'][1]['peakNavd88Ft'],3.2);self.assertEqual(out['archive']['endDate'],'2026-10-28');self.assertEqual(out['archive']['classificationCounts']['moderate'],1)
  for key in ('station','datum','thresholds','tideModel','verticalUncertaintyFt','topEvents'):self.assertEqual(out[key],s[key])
 def test_stale_measurements_rejected_even_with_fresh_run_time(self):
  now=datetime(2026,10,28,12,tzinfo=timezone.utc)
  with self.assertRaisesRegex(AssertionError,'stale'):merge(baseline(),[(now-timedelta(hours=7),1)],now,[])
 def test_wrong_gauge_datum_and_thresholds_rejected(self):
  for path,value in [(('station','usgsGaugeId'),'01407601'),(('datum','mllwOffsetFromNavd88Ft'),1.5),(('thresholds','navd88','minor'),3.5)]:
   s=baseline();p=s
   for k in path[:-1]:p=p[k]
   p[path[-1]]=value
   with self.assertRaises(AssertionError):validate_stats(s)
