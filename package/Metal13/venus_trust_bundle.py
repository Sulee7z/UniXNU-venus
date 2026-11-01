"""Merge v2 entries into the first static module, preserving every entry's attributes."""
import hashlib
import struct
import uuid


def entries(bundle):
    if len(bundle)<8:raise ValueError('Truncated trust bundle')
    count=struct.unpack_from('<I',bundle)[0]
    if not 0<count<=128 or len(bundle)<4+4*count:raise ValueError('Invalid module count')
    starts=list(struct.unpack_from('<'+str(count)+'I',bundle,4))+[len(bundle)]
    if starts[0]!=4+4*count or any(a>=b or a%4 for a,b in zip(starts,starts[1:])):
        raise ValueError('Invalid module offsets')
    result={}
    for start,end in zip(starts,starts[1:]):
        if end-start<24 or struct.unpack_from('<I',bundle,start)[0]!=2:raise ValueError('Expected a v2 module')
        size=struct.unpack_from('<I',bundle,start+20)[0]
        if end-start!=24+24*size:raise ValueError('Module extent mismatch')
        previous=None
        for at in range(start+24,end,24):
            key,attrs=bundle[at:at+20],bundle[at+20:at+24]
            if previous is not None and previous>=key:raise ValueError('Unsorted or duplicate module entry')
            if attrs[0] not in (1,2,3,4) or attrs[3]:raise ValueError('Invalid entry attributes')
            if key in result and result[key]!=attrs:raise ValueError('Conflicting original entry attributes')
            result[key]=attrs;previous=key
    return result


def merge_static(bundle, additions):
    original=entries(bundle)
    merged=dict(original)
    for key,attrs in additions:
        if len(key)!=20 or len(attrs)!=4 or attrs[0] not in (1,2,3,4) or attrs[3]:
            raise ValueError('Invalid owner entry')
        if key in merged and merged[key]!=attrs:raise ValueError('Owner entry changes existing attributes')
        merged[key]=attrs
    body=b''.join(key+merged[key] for key in sorted(merged))
    identifier=uuid.uuid5(uuid.NAMESPACE_URL,'venus-static-trust:'+hashlib.sha256(body).hexdigest())
    module=struct.pack('<I16sI',2,identifier.bytes,len(merged))+body
    result=struct.pack('<II',1,8)+module
    parsed=entries(result)
    if any(parsed[key]!=attrs for key,attrs in original.items()):raise ValueError('Original entry lost')
    return result,{'original_entries':len(original),'merged_entries':len(parsed),
                   'new_entries':len(parsed)-len(original),'all_original_attributes_preserved':True}
