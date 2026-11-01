#!/usr/bin/env python3
"""Record source-backed ST protocol differences without selecting a driver."""
import hashlib
import json
from pathlib import Path

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-touch-source-reference'
sources=json.loads((OUT/'sources.json').read_text())
for name,record in sources['files'].items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==record['sha256']
def text(family,name):return (OUT/'drivers/input/touchscreen'/family/name).read_text()
spi=text('fts_spi','fts.c');old=text('st','fts.c');hw=text('fts_spi','fts_lib/ftsHardware.h')
io=text('fts_spi','fts_lib/ftsIO.c')
assert '.compatible = "st,spi"' in spi and 'client->mode = SPI_MODE_0' in spi
assert 'client->bits_per_word = 8' in spi and '#define SPI_CLOCK_FREQ' in hw and '7000000' in hw
assert 'struct spi_transfer transfer[2] = { {0}, {0} };' in io and 'transfer[1].delay_usecs = SPI_DELAY_CS;' in io
assert 'touchId = (event[1] & 0xF0) >> 4;' in spi and 'touchId = event[1] & 0x0F;' in old
assert '"fts,thp-fw-name"' in spi and '"fts,htp-fw-name"' not in spi
record={'device':'venus','date':'2026-10-28','repository':sources['repository'],'commit':sources['commit'],
    'sources_manifest_sha256':hashlib.sha256((OUT/'sources.json').read_bytes()).hexdigest(),
    'families':{
        'st':{'driver_version':'4.2.14','default_transport':'I2C','touch_id_bits':'event[1] low nibble',
              'xy_layout':'x=(event[2]<<4)|(event[4]>>4); y=(event[3]<<4)|(event[4]&15)'},
        'fts_spi':{'driver_version':'5.2.4.1','compatible':'st,spi','default_transport':'4-wire SPI',
                   'spi_mode':0,'word_bits':8,'clock_hz':7000000,'cs_post_read_delay_us':10,
                   'touch_id_bits':'event[1] high nibble','touch_type_bits':'event[1] low nibble',
                   'normal_xy_layout':'x=((event[3]&15)<<8)|event[2]; y=(event[4]<<4)|(event[3]>>4)',
                   'super_resolution_layout':'alternate16-bit XY enabled by board policy',
                   'fifo_event_bytes':8,'fifo_depth':32,'fifo_read_opcode':'0x87',
                   'hardware_read_opcode':'0xfb','chip_id_address':'0x20000000',
                   'source_selected_chip_family':'SALIXP','source_expected_id_bytes':['0x36','0x40'],
                   'actual_venus_chip_id_observed':None}},
    'mismatches':['The pinned kernel fts_spi parser reads fts,thp-fw-name; the retained live Venus DT declares fts,htp-fw-name.',
                  'The pinned fts_spi source does not contain the live DT avddold supply path; target supply responsibility still needs reconciliation.',
                  'The I2C-oriented st4.x and SPI fts5.x drivers use different chip registers and touch ID/coordinate encodings.'],
    'implementation_gate':['Confirm the stock driver/firmware generation and exact chip ID before adopting the source-selected SALIXP constant',
                           'Preserve CS through command/read phases and the dummy-byte rules; validate the GENI transfer path',
                           'Parse the actual firmware and report protocol, then bound contact IDs and use coherent HID snapshots'],
    'driver_selected_or_compiled':False,'phone_operation_performed':False,
    'scope':'Pinned Linux source comparison and concrete integration gaps; expected source values are not physical Venus measurements'}
(DEVICE/'evidence/touch-reference-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: pinned ST SPI source located; protocol family and live-DT supply/firmware-key differences recorded')
print('Expected source SALIXP ID36/40 remains unmeasured; no physical input driver enabled')
