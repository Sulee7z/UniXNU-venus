"""Bounded, read-only QuartzCore/MobileGestalt scale inspection in the deployed cache."""
import json
import re
import struct
import subprocess


def inspect_scale(original, images, slides, out):
    def read(va, n): return original(va, n)[0]
    def u64(va): return struct.unpack('<Q', read(va, 8))[0]
    def pointer(va):
        raw = u64(va)
        for file, info in slides:
            begin, size, _, offset, slide_size, _, _, _ = info
            if begin <= va < begin+size and slide_size:
                h = file.read(offset, min(slide_size, 40))
                version = struct.unpack_from('<I', h)[0]
                if version == 2:
                    mask, add = struct.unpack_from('<QQ', h, 24)
                    value = raw & ~mask
                    return value+add if value else 0
                if version not in (0, 1): raise ValueError('Unsupported pointer slide')
        return raw
    def cstring(va):
        data = bytearray()
        for i in range(1024):
            c = read(va+i, 1)
            if c == b'\0': return data.decode()
            data += c
        raise ValueError('Unterminated metadata string')
    def sections(base):
        h = struct.unpack('<8I', read(base, 32))
        assert h[0] == 0xfeedfacf and h[5] < 65536
        cmds = read(base+32, h[5]); at = 0; found = []
        for _ in range(h[4]):
            cmd, size = struct.unpack_from('<II', cmds, at)
            assert size >= 8 and at+size <= len(cmds)
            if cmd == 0x19:
                n = struct.unpack_from('<I', cmds, at+64)[0]
                for i in range(n):
                    sect, seg, va, length = struct.unpack_from('<16s16sQQ', cmds, at+72+i*80)
                    found.append((sect.rstrip(b'\0').decode(), va, length))
            at += size
        return found
    def disasm(va, size, label):
        blob = read(va, size)
        result = subprocess.run(['/usr/bin/llvm-mc','--triple=aarch64','--disassemble'],
            input=' '.join(f'0x{x:02x}' for x in blob), text=True, capture_output=True, check=True)
        lines = [s.strip() for s in result.stdout.splitlines() if s.strip() and s.strip()!='.text']
        assert len(lines) == size//4, result.stderr
        regs={}; annotated=[]
        for i,line in enumerate(lines):
            pc=va+4*i; w=struct.unpack_from('<I',blob,4*i)[0];rd=w&31;rn=(w>>5)&31;note='';ref=None
            if w&0x9f000000==0x90000000:
                imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
                if imm&(1<<20):imm-=1<<21
                regs[rd]=(pc&~4095)+(imm<<12)
            elif w&0xffc00000==0x91000000 and rn in regs:
                regs[rd]=regs[rn]+((w>>10)&4095);ref=regs[rd]
            elif w&0xffc00000==0xf9400000 and rn in regs:
                ref=regs[rn]+((w>>10)&4095)*8;regs.pop(rd,None)
            elif w&0x7c000000==0x14000000:
                imm=w&0x3ffffff
                if imm&(1<<25):imm-=1<<26
                dest=pc+imm*4;note=' -> '+hex(dest)
                owner=next((im[2] for im in images if im[0]<=dest<im[0]+im[1]),'stub')
                note+=' '+owner
                if w&0x80000000:
                    for r in range(19):regs.pop(r,None)
            if ref is not None:
                try: note=' ref '+hex(ref)+' '+repr(read(ref,32))
                except ValueError: pass
            annotated.append(f'{pc:#x} {line}{note}')
        (out/(label+'.txt')).write_text('\n'.join(annotated)+'\n')
    report = {}
    for short in ('QuartzCore', 'IOMobileFramebuffer', 'libMobileGestalt.dylib'):
        matches = [im for im in images if im[2].endswith('/'+short)]
        assert len(matches) == 1, (short, matches)
        im = matches[0]; secs = sections(im[0]); strings = {}; classes = {}
        for name, va, size in secs:
            if name in ('__cstring','__objc_methname'):
                blob = read(va, size)
                for m in re.finditer(rb'[^\x00]+\x00', blob):
                    if re.search(rb'scale|pitch', m[0], re.I): strings[va+m.start()] = m[0][:-1].decode(errors='replace')
        for name, va, size in secs:
            if name not in ('__cfstring', '__objc_selrefs'): continue
            stride = 32 if name=='__cfstring' else 8
            for at in range(va, va+size, stride):
                ptr = pointer(at+16 if stride==32 else at)
                if ptr in strings: strings[at] = strings[ptr]
        for name, va, size in secs:
            if name != '__objc_classlist': continue
            for at in range(va, va+size, 8):
                cls = pointer(at); ro = pointer(cls+32)&~7
                cname = cstring(pointer(ro+24))
                if 'DisplayMode' not in cname: continue
                ivars = []; ilist = pointer(ro+48)
                if ilist:
                    stride, count = struct.unpack('<II', read(ilist, 8))
                    assert stride==32 and count<128
                    for i in range(count):
                        entry = ilist+8+i*stride
                        ivars.append({'name':cstring(pointer(entry+8)), 'offset':struct.unpack('<I',read(pointer(entry),4))[0]})
                methods = []; mlist = pointer(ro+32)
                if mlist:
                    bits, count = struct.unpack('<II', read(mlist, 8)); stride = bits&0xfffc
                    assert stride in (12,24) and count<512
                    for i in range(count):
                        entry = mlist+8+i*stride
                        if bits&0x80000000:
                            n,t,p = struct.unpack('<iii',read(entry,12)); imp=entry+8+p; types=cstring(entry+4+t)
                        else:
                            imp=pointer(entry+16); types=cstring(pointer(entry+8))
                        methods.append({'pc':hex(imp),'types':types})
                        if types in ('Q16@0:8','d16@0:8') or 'init' in types:
                            disasm(imp,64,short+'-getter-'+hex(imp))
                classes[cname] = {'ivars':ivars, 'methods':methods}
        refs=[]
        for name,va,size in secs:
            if name!='__text': continue
            blob=read(va,size); regs={}
            for off in range(0,size-3,4):
                pc=va+off; w=struct.unpack_from('<I',blob,off)[0]; rd=w&31; rn=(w>>5)&31
                ref=None
                if w&0x9f000000==0x90000000:
                    imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
                    if imm&(1<<20):imm-=1<<21
                    regs[rd]=(pc&~4095)+(imm<<12)
                elif w&0xffc00000==0x91000000 and rn in regs:
                    regs[rd]=regs[rn]+((w>>10)&4095);ref=regs[rd]
                elif w&0xffc00000==0xf9400000 and rn in regs:
                    ref=regs[rn]+((w>>10)&4095)*8;regs.pop(rd,None)
                elif w&0xfc000000==0x94000000:
                    for r in range(19):regs.pop(r,None)
                if ref in strings:
                    row={'pc':hex(pc),'text':strings[ref]};refs.append(row)
                    if re.search('display.?scale|preferredScale|dot-pitch|scale',row['text'],re.I):
                        begin=max(va,pc-128); n=min(384,va+size-begin)
                        disasm(begin,n,short+'-ref-'+hex(pc))
        # Tables may name a key and its callback without an ADRP string xref.
        tables=[]
        if short=='libMobileGestalt.dylib':
            targets={k:v for k,v in strings.items() if v in ('main-screen-scale','display-scale')}
            for name,va,size in secs:
                if name not in ('__const','__data'): continue
                for at in range(va,va+size-7,8):
                    p=pointer(at)
                    if p in targets:
                        values=[pointer(at+8*i) for i in range(-4,9)]
                        tables.append({'at':hex(at),'key':targets[p],'words':[hex(v) for v in values]})
                        for v in values:
                            if im[0]<=v<im[0]+im[1] and not v&3:
                                disasm(v,512,'MG-table-'+hex(v))
        report[short]={'image':im[2], 'classes':classes, 'references':refs, 'strings':{hex(k):v for k,v in strings.items()},'tables':tables}
    disasm(0x18f6e545c, 96, 'BaseBoard-zero-helper')
    for va,size,label in ((0x1a0215704,0x900,'MG-display-answers'),
                          (0x1a020fb6c,0x400,'MG-DT-u32'),
                          (0x1a02111c4,0x480,'MG-DT-property'),
                          (0x1a0216000,0x220,'MG-display-answers-tail'),
                          (0x1a020d0d4,0x500,'MG-typed-answer'),
                          (0x18954bfa4,0x160,'QuartzCore-mode-constructor')):
        disasm(va,size,label)
    call=0x18957079c
    word=struct.unpack('<I',read(call,4))[0];imm=word&0x3ffffff
    if imm&(1<<25):imm-=1<<26
    target=call+imm*4
    disasm(target,64,'main-screen-scale-stub')
    a,b,c=struct.unpack('<3I',read(target,12))
    if a&0x9f00001f==0x90000010 and b&0xffc003ff==0x91000210 and c==0xd61f0200:
        imm=((a>>5)&0x7ffff)*4+((a>>29)&3)
        if imm&(1<<20):imm-=1<<21
        resolved=(target&~4095)+(imm<<12)+((b>>10)&4095)
        disasm(resolved,1024,'main-screen-scale-reader')
        report['scale_reader']=hex(resolved)
    (out/'scale-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Scale inspection saved:',out/'scale-inspection.json')
