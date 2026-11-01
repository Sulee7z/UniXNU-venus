"""Read-only ARM64/reference inspection of the pinned FrontBoardServices trap."""
import json
import struct
import subprocess


def inspect(original, images, slides, pc, output, identity):
    def read(va, n):
        return original(va,n)[0]

    def u32(va):
        return struct.unpack('<I',read(va,4))[0]

    def u64(va):
        return struct.unpack('<Q',read(va,8))[0]

    def cstring(va, cap=2048):
        result = bytearray()
        for i in range(cap):
            b = read(va+i,1)[0]
            if not b:
                return result.decode('utf-8',errors='replace')
            result.append(b)
        return result.decode('utf-8',errors='replace')+'<truncated>'

    slide_versions = {}
    def pointer(va):
        raw = u64(va)
        for file, info in slides:
            begin,size,offset,slide_offset,slide_size,flags,maxprot,prot = info
            if begin<=va<begin+size and slide_size:
                h = file.read(slide_offset,min(slide_size,40))
                version = struct.unpack_from('<I',h)[0]
                slide_versions[hex(begin)] = version
                if version==2:
                    mask,add = struct.unpack_from('<QQ',h,24)
                    value = raw & ~mask
                    return value+add if value else 0
                if version not in (0,1):
                    raise ValueError(f'Unsupported pointer slide version {version} at {va:#x}')
        return raw

    owner = next(im for im in images if im[0]<=pc<im[0]+im[1])
    base = owner[0]
    magic,cpu,subtype,kind,ncmds,cmdbytes,flags,reserved = struct.unpack('<8I',read(base,32))
    if magic!=0xfeedfacf or not 0<ncmds<512 or cmdbytes>65536:
        raise ValueError('Unexpected framework Mach-O header')
    sections = []
    commands = read(base+32,cmdbytes)
    at = 0
    for _ in range(ncmds):
        cmd,size = struct.unpack_from('<II',commands,at)
        if size<8 or at+size>len(commands):
            raise ValueError('Invalid Mach-O load command')
        if cmd==0x19:
            count = struct.unpack_from('<I',commands,at+64)[0]
            for i in range(count):
                pos = at+72+i*80
                sect,seg,va,n = struct.unpack_from('<16s16sQQ',commands,pos)
                sections.append({'section':sect.rstrip(b'\0').decode(),'segment':seg.rstrip(b'\0').decode(),
                                 'va':va,'size':n})
        at += size

    def describe(va):
        d = {'address':hex(va)}
        sec = next((s for s in sections if s['va']<=va<s['va']+s['size']),None)
        if sec:
            d['section'] = sec['segment']+','+sec['section']
        image = next((im for im in images if im[0]<=va<im[0]+im[1]),None)
        if image:
            d['image'] = image[2]
        try:
            if sec and sec['section'] in ('__cstring','__objc_methname','__objc_classname'):
                d['string'] = cstring(va)
            elif sec and sec['section']=='__cfstring':
                loc = sec['va']+((va-sec['va'])//32)*32
                length = u64(loc+24)
                ptr = pointer(loc+16)
                d.update(cfstring_record=hex(loc),length=length,string_address=hex(ptr))
                if 0<length<4096:
                    d['string'] = read(ptr,length).decode('utf-8',errors='replace')
            elif sec and sec['section']=='__objc_selrefs':
                ptr = pointer(va)
                d.update(target=hex(ptr),selector=cstring(ptr))
            elif sec and sec['section']=='__objc_data':
                ro = pointer(va+32)&~7
                d.update(class_ro=hex(ro),class_name=cstring(pointer(ro+24)))
            else:
                d['first16'] = read(va,16).hex()
        except (ValueError,struct.error) as error:
            d['unresolved'] = str(error)
        return d

    def signed(v, bits):
        return v-(1<<bits) if v & (1<<(bits-1)) else v

    def disassemble(begin, size):
        blob = read(begin,size)
        result = subprocess.run(['/usr/bin/llvm-mc','--triple=aarch64','--disassemble'],
            input=' '.join(f'0x{b:02x}' for b in blob),text=True,capture_output=True,check=True)
        lines = [s.strip() for s in result.stdout.splitlines() if s.strip() and s.strip()!='.text']
        if len(lines)!=size//4:
            raise ValueError('Instruction count mismatch: '+result.stderr)
        return blob,lines

    def walk(begin,size):
        blob,assembly = disassemble(begin,size)
        regs,records,targets = {},[],set()
        for i in range(size//4):
            here = begin+i*4
            word = struct.unpack_from('<I',blob,i*4)[0]
            rd,rn = word&31,(word>>5)&31
            record = {'pc':hex(here),'word':f'{word:08x}','asm':assembly[i]}
            ref = None
            if word&0x9f000000==0x90000000: # ADRP
                imm = signed(((word>>5)&0x7ffff)*4+((word>>29)&3),21)
                regs[rd] = (here&~4095)+(imm<<12)
                record['page'] = hex(regs[rd])
            elif word&0xff000000==0x91000000 and rn in regs: # ADD immediate, 64-bit
                regs[rd] = regs[rn]+(((word>>10)&4095)<<(12 if word&(1<<22) else 0))
                ref = regs[rd]
            elif word&0xffc00000==0xf9400000 and rn in regs: # LDR unsigned offset, 64-bit
                ref = regs[rn]+((word>>10)&4095)*8
                try:
                    value = pointer(ref)
                    regs[rd] = value
                    record['loaded_pointer'] = describe(value) if value else {'address':'0x0'}
                except ValueError as error:
                    record['pointer_error'] = str(error)
                    regs.pop(rd,None)
            elif word&0x7c000000==0x14000000: # B / BL
                target = here+(signed(word&0x3ffffff,26)<<2)
                record['branch'] = describe(target)
                targets.add(target)
                if word&0x80000000:
                    for r in range(19):
                        regs.pop(r,None)
            if ref is not None:
                record['reference'] = describe(ref)
            records.append(record)
        return records,targets

    records,targets = walk(pc-0x300,0x310)
    callers = {}
    for address in identity['addresses'][2:]:
        if address.get('image')!=owner[2] or 'unslid_va' not in address:
            continue
        callsite = int(address['unslid_va'],16)
        rows,more = walk(callsite-0x180,0x1a0)
        callers[hex(callsite)] = rows
        targets.update(more)
    # The receiver class is reached by the initializer's audited classref.
    classes = {}
    for row in records:
        item = row.get('loaded_pointer',{})
        if item.get('class_name')!='FBSDisplayMode':
            continue
        ro = int(item['class_ro'],16)
        methods = pointer(ro+32)
        bits,count = struct.unpack('<II',read(methods,8))
        stride = bits&0xfffc # low two bits are the Objective-C fixed-up flags
        if not 0<count<512 or stride not in (12,24):
            raise ValueError(f'Unexpected FBSDisplayMode method list {methods:#x}: {bits:#x}, count={count}')
        found = []
        for i in range(count):
            entry = methods+8+i*stride
            if bits&0x80000000:
                name,type_name,imp = struct.unpack('<iii',read(entry,12))
                # Direct relative selectors in this optimized cache use a
                # shared selector base, not necessarily the entry address.
                # Leave them unresolved; caller __objc_stubs independently
                # expose their selector through audited selrefs.
                selector = None if bits&0x40000000 else cstring(pointer(entry+name))
                type_name = entry+4+type_name
                imp = entry+8+imp
            else:
                name,type_name,imp = pointer(entry),pointer(entry+8),pointer(entry+16)
                selector = cstring(name)
            found.append({'selector':selector,'types':cstring(type_name),'implementation':hex(imp)})
        ivars = []
        ilist = pointer(ro+48)
        if ilist:
            stride,count = struct.unpack('<II',read(ilist,8))
            if stride!=32 or count>128:
                raise ValueError('Unexpected FBSDisplayMode ivar list')
            for i in range(count):
                entry = ilist+8+i*stride
                ivars.append({'name':cstring(pointer(entry+8)),'types':cstring(pointer(entry+16)),
                              'offset':u32(pointer(entry)),'size':u32(entry+28)})
        classes['FBSDisplayMode'] = {'address':item['address'],'methods':found,'ivars':ivars}
        break
    stubs = {}
    for target in sorted(targets):
        if pc-0x300<=target<pc+16:
            continue
        try:
            rows,_ = walk(target,48)
            stubs[hex(target)] = rows
        except (ValueError,subprocess.CalledProcessError) as error:
            stubs[hex(target)] = {'unresolved':str(error)}
    report = {'image':owner[2],'image_base':hex(base),'pc':hex(pc),
        'identity':identity,'sections':sections,'pointer_slide_versions':slide_versions,
        'instructions':records,'caller_windows':callers,'classes':classes,'call_target_prefixes':stubs,
        'limits':'Static references from bounded instruction windows; register tracking is not runtime execution or a full control-flow proof.'}
    (output/'frontboard-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    text = []
    for row in records:
        notes = {k:v for k,v in row.items() if k not in ('pc','word','asm')}
        text.append(row['pc']+' '+row['word']+' '+row['asm']+(' ; '+json.dumps(notes) if notes else ''))
    (output/'frontboard-inspection.txt').write_text('\n'.join(text)+'\n')
    for callsite,rows in callers.items():
        (output/f'caller-{callsite}.txt').write_text('\n'.join(
            row['pc']+' '+row['asm']+' ; '+json.dumps({k:v for k,v in row.items() if k not in ('pc','word','asm')})
            for row in rows)+'\n')
    print('FrontBoard instruction/reference inspection:', output/'frontboard-inspection.json')
