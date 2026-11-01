// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cstddef>
#include <cstdint>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
typedef size_t VG_SIZE;
typedef uint64_t VG_LBA;
#include "VenusGptTransaction.h"
#include "GeneratedPlan.h"
struct Fixture {
  std::vector<unsigned char> primary, backup;
  unsigned calls = 0, fail = 0, writes = 0;
  std::vector<VG_LBA> order;
  bool corruptReadback = false;
};
static int read(void *v, VG_LBA lba, VG_SIZE size, void *dst)
{
  auto &f = *static_cast<Fixture *>(v);
  if (++f.calls == f.fail) return 0;
  assert(lba == 0 || lba == VG_BACKUP_LBA);
  auto &bytes = lba ? f.backup : f.primary;
  assert(size == bytes.size()); memcpy(dst, bytes.data(), size);
  if (f.corruptReadback && f.writes) static_cast<unsigned char *>(dst)[0] ^= 1;
  return 1;
}
static int write(void *v, VG_LBA lba, VG_SIZE size, const void *src)
{
  auto &f = *static_cast<Fixture *>(v);
  ++f.writes; f.order.push_back(lba);
  if (++f.calls == f.fail) return 0;
  assert(lba == 0 || lba == VG_BACKUP_LBA);
  auto &bytes = lba ? f.backup : f.primary;
  assert(size == bytes.size()); memcpy(bytes.data(), src, size); return 1;
}
static int flush(void *v) { auto &f = *static_cast<Fixture *>(v); return ++f.calls != f.fail; }
int main()
{
  VG_PLAN p = {VG_BACKUP_LBA,sizeof(VgPrimaryBefore),sizeof(VgBackupBefore),VgPrimaryBefore,VgBackupBefore,VgPrimaryAfter,VgBackupAfter};
  std::vector<unsigned char> scratch(sizeof(VgPrimaryBefore));
  auto fresh = [] { Fixture f; f.primary.assign(VgPrimaryBefore,VgPrimaryBefore+sizeof(VgPrimaryBefore));
                   f.backup.assign(VgBackupBefore,VgBackupBefore+sizeof(VgBackupBefore)); return f; };
  auto run = [&](Fixture &f, bool apply) { VG_IO io = {&f,read,write,flush}; return VgTransaction(&p,&io,scratch.data(),scratch.size(),apply); };
  auto f=fresh(); assert(run(f,false)==VG_OK && f.writes==0);
  assert(run(f,true)==VG_OK && f.order==std::vector<VG_LBA>({VG_BACKUP_LBA,0}));
  f.writes=0; assert(run(f,true)==VG_ALREADY_APPLIED && f.writes==0);
  f=fresh(); f.primary[400]^=1; assert(run(f,true)==VG_BEFORE_MISMATCH && f.writes==0);
  f=fresh(); f.backup.assign(VgBackupAfter,VgBackupAfter+sizeof(VgBackupAfter));
  assert(run(f,true)==VG_BEFORE_MISMATCH && f.writes==0);
  const unsigned errors[]={VG_READ_BEFORE,VG_READ_BEFORE,VG_WRITE_BACKUP,VG_FLUSH_BACKUP,VG_VERIFY_BACKUP,VG_WRITE_PRIMARY,VG_FLUSH_PRIMARY,VG_VERIFY_PRIMARY};
  for(unsigned n=1;n<=8;++n) {
    f=fresh(); f.fail=n; assert(run(f,true)==errors[n-1]);
    if(n<=5) assert(f.primary==std::vector<unsigned char>(VgPrimaryBefore,VgPrimaryBefore+sizeof(VgPrimaryBefore)));
  }
  f=fresh(); f.corruptReadback=true; assert(run(f,true)==VG_VERIFY_BACKUP && f.writes==1);
  puts("PASS: actual GPT regions, preview/no-write, backup-first ordered writeback, idempotence and all eight failure boundaries");
}
