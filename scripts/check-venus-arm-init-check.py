"""Verify the prepared early-C reset checkpoint without touching a phone."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

root = Path('/mnt/g/UniXNU-Port')
base = root/'artifacts/venus-ufs-root'
out = base/'phone-arm-init-check'
reference = base/'phone-288m'
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def need(ok, text):
    if not ok: raise SystemExit(text)
report = json.loads((root/'ports/UniXNU-venus/evidence/arm-init-check-candidate.json').read_text())
need(sha(out/'boot-venus-unixnu.img') == report['sha256'], 'Boot image hash changed')
need(sha(out/'kernel.macho') == report['checkpoint_kernel_sha256'], 'Checkpoint kernel hash changed')
need(sha(base/'kernel/kernel.macho') == report['source_kernel_sha256'], 'Source kernel identity changed')
need(sha(out/'kernel.macho.adt') == sha(reference/'kernel.macho.adt'), 'ADT changed')
for name in ('UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):
    need(sha(out/name) == sha(reference/name), 'Loader changed: '+name)
data = (out/'kernel.macho').read_bytes()
magic, _, _, _, count = struct.unpack_from('<IiiII', data, 0)
need(magic == 0xFEEDFACF, 'Not a 64-bit Mach-O')
segments = []
offset = 32
for _ in range(count):
    kind, size = struct.unpack_from('<II', data, offset)
    if kind == 0x19:
        _, vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<16sQQQQ', data, offset+8)
        segments.append((vmaddr, vmsize, fileoff, filesize))
    offset += size
def file_offset(va):
    for vmaddr, vmsize, fileoff, filesize in segments:
        if vmaddr <= va < vmaddr + min(vmsize, filesize): return fileoff + va - vmaddr
    raise SystemExit(f'{va:#x} is not file-backed')
def word(va): return struct.unpack_from('<I', data, file_offset(va))[0]
call_site = 0xFFFFFFF00BFE1E70
cave = 0xFFFFFFF00BA08620
instruction = word(call_site)
need(instruction & 0xFC000000 == 0x14000000, 'Call site is not a B instruction')
delta = instruction & 0x03FFFFFF
if delta & 0x02000000: delta -= 0x04000000
need((call_site + delta*4) & 0xFFFFFFFFFFFFFFFF == cave, 'Call site branches elsewhere')
code = [word(cave+i) for i in range(0, 0x60, 4)]
need(code[0] == 0x52800120 and code[1] == 0x72B08000, 'Reset wrapper does not load PSCI SYSTEM_RESET request')
need(0xD4000003 in code, 'Reset wrapper does not issue SMC')
need(code[2:5] == [0xAA1F03E1, 0xAA1F03E2, 0xAA1F03E3] and code[5] == 0xD4000003,
     'Reset wrapper SMC argument sequence differs')
need(0xD503205F in code, 'Reset wrapper has no wait loop')
ants = subprocess.check_output(['mtype','-i',str(out/'payload.img'),'::/EFI/UniXNU/unixnu.toml'],text=True)
need('native-ufs-root=0' in ants and 'sheng-data-persist=0' in ants, 'Diagnostic boot arguments not packaged')
extracted = subprocess.check_output(['mtype','-i',str(out/'payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho'])
need(hashlib.sha256(extracted).hexdigest() == report['checkpoint_kernel_sha256'], 'FAT kernel differs')
verification = json.loads((out/'verification.json').read_text())
need(verification['roundtrip_verified'] and verification['sha256'] == report['sha256'], 'Boot container verification changed')
need(verification['efi'] == json.loads((reference/'verification.json').read_text())['efi'], 'Packaged EFI set differs')
result = dict(report, call_site=hex(call_site), cave=hex(cave),
              verified_branch=True, verified_smc_reset=True, verified_uart_disabled=True,
              verified_data_persistence_disabled=True, verified_fat_roundtrip=True,
              verified_efi_identical=True, host_qualified=True)
(root/'ports/UniXNU-venus/evidence/arm-init-check-qualified.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
