// SPDX-License-Identifier: BSD-2-Clause-Patent
// Caller supplies VG_SIZE/VG_LBA and exact host-validated before/after regions.
typedef struct {
  void *context;
  int (*read)(void *, VG_LBA, VG_SIZE, void *);
  int (*write)(void *, VG_LBA, VG_SIZE, const void *);
  int (*flush)(void *);
} VG_IO;
typedef struct {
  VG_LBA backup_lba;
  VG_SIZE primary_bytes, backup_bytes;
  const unsigned char *primary_before, *backup_before, *primary_after, *backup_after;
} VG_PLAN;
enum {
  VG_OK = 0, VG_ALREADY_APPLIED = 1, VG_BAD_ARGUMENT = 2,
  VG_READ_BEFORE = 3, VG_BEFORE_MISMATCH = 4,
  VG_WRITE_BACKUP = 5, VG_FLUSH_BACKUP = 6, VG_VERIFY_BACKUP = 7,
  VG_WRITE_PRIMARY = 8, VG_FLUSH_PRIMARY = 9, VG_VERIFY_PRIMARY = 10
};
static int VgEqual(const void *a, const void *b, VG_SIZE size)
{
  const unsigned char *x = (const unsigned char *)a, *y = (const unsigned char *)b;
  VG_SIZE i;
  for (i = 0; i < size; ++i) if (x[i] != y[i]) return 0;
  return 1;
}
static unsigned VgTransaction(const VG_PLAN *p, const VG_IO *io, void *scratch, VG_SIZE capacity, int apply)
{
  int before, after;
  if (!p || !io || !scratch || !io->read || !io->write || !io->flush ||
      p->primary_bytes != 6U * 4096U || p->backup_bytes != 5U * 4096U ||
      capacity < p->primary_bytes || p->backup_lba < 6 ||
      !p->primary_before || !p->backup_before || !p->primary_after || !p->backup_after) return VG_BAD_ARGUMENT;
  if (!io->read(io->context, 0, p->primary_bytes, scratch)) return VG_READ_BEFORE;
  before = VgEqual(scratch, p->primary_before, p->primary_bytes);
  after = VgEqual(scratch, p->primary_after, p->primary_bytes);
  if (!io->read(io->context, p->backup_lba, p->backup_bytes, scratch)) return VG_READ_BEFORE;
  before = before && VgEqual(scratch, p->backup_before, p->backup_bytes);
  after = after && VgEqual(scratch, p->backup_after, p->backup_bytes);
  if (after) return VG_ALREADY_APPLIED;
  if (!before) return VG_BEFORE_MISMATCH;
  if (!apply) return VG_OK;
  if (!io->write(io->context, p->backup_lba, p->backup_bytes, p->backup_after)) return VG_WRITE_BACKUP;
  if (!io->flush(io->context)) return VG_FLUSH_BACKUP;
  if (!io->read(io->context, p->backup_lba, p->backup_bytes, scratch) ||
      !VgEqual(scratch, p->backup_after, p->backup_bytes)) return VG_VERIFY_BACKUP;
  if (!io->write(io->context, 0, p->primary_bytes, p->primary_after)) return VG_WRITE_PRIMARY;
  if (!io->flush(io->context)) return VG_FLUSH_PRIMARY;
  if (!io->read(io->context, 0, p->primary_bytes, scratch) ||
      !VgEqual(scratch, p->primary_after, p->primary_bytes)) return VG_VERIFY_PRIMARY;
  return VG_OK;
}
