#!/usr/bin/env python3
"""Check production probe JSON and API-call semantics before runtime integration."""
import hashlib
import json
from pathlib import Path
import subprocess

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-mg-query-probe/host-tests';OUT.mkdir(exist_ok=True)
source=DEVICE/'tests/mg_query_protocol.c';binary=OUT/'check'
subprocess.run(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
                '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',str(DEVICE/'package'),
                str(source),'-o',str(binary)],check=True,timeout=60)
reports=[]
for name in ('success','library-failure','api-failure'):
    result=subprocess.run([str(binary),name],capture_output=True,text=True,timeout=30)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    result.check_returncode();report=json.loads(result.stdout)
    assert report['complete']==(name=='success')
    if name=='success':
        assert report['device_tree'][0]['entry_found'] and not report['device_tree'][1]['entry_found']
        assert report['device_tree'][0]['display-scale']['hex']=='02000000'
        assert [r['default_bits'] for r in report['float_answers']]==['3f800000','40000000','40e00000']
        assert all(r['return_bits']=='00000000' for r in report['float_answers'])
        assert report['copy_answers']['MainScreenStaticInfo']['answer']['length']==24
        assert report['boot_uuid']=='01234567-89AB-CDEF-0123-456789ABCDEF'
    reports.append(report)
record={'passed':True,'production_source_sha256':hashlib.sha256((DEVICE/'package/MGQueryProbe.c').read_bytes()).hexdigest(),
        'fixture_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':reports,
        'scope':'Actual probe C executes under ASan/UBSan with explicit mock APIs. No actual MG library was loaded.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: actual probe JSON, exact questions/defaults/paths, cached-zero versus property2, API failures and cleanup')
