// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
// Bounded, partition-independent GPT measurement. No manifest or data-window
// reads. Callers supply a capacity already obtained from READ CAPACITY(10).
namespace VenusUfsGptRead {
struct Result {
  const char *error = nullptr;
  uint32_t reads = 0, entries = 0, used = 0, primaryCrc = 0, backupCrc = 0, entriesCrc = 0;
  uint64_t lastLba = 0, firstUsable = 0, lastUsable = 0, entriesLba = 0, backupEntriesLba = 0;
};
inline uint32_t le32(const uint8_t *p) { return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24; }
inline uint64_t le64(const uint8_t *p) { return le32(p) | uint64_t(le32(p + 4)) << 32; }
inline uint32_t crc32(const uint8_t *data, unsigned bytes, bool header = false)
{
  uint32_t crc = 0xffffffffU;
  for (unsigned i = 0; i < bytes; ++i) {
    crc ^= header && i >= 16 && i < 20 ? 0 : data[i];
    for (unsigned bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1)));
  }
  return ~crc;
}
inline bool used(const uint8_t *p)
{
  for (unsigned i = 0; i < 16; ++i) if (p[i]) return true;
  return false;
}
template<class Read>
Result collect(uint32_t blockBytes, uint64_t lastLba, uint8_t *scratch, unsigned scratchBytes, Read read)
{
  Result r;
  r.lastLba = lastLba;
  if (blockBytes != 4096 || lastLba < 12 || lastLba >= 0xffffffffULL || !scratch || scratchBytes < 32768) {
    r.error = "unsupported capacity or scratch extent"; return r;
  }
  uint8_t *primary = scratch, *backup = scratch + 4096, *array = scratch + 8192;
  auto fetch = [&](uint64_t lba, unsigned blocks, uint8_t *dst) {
    if (!blocks || blocks > 4 || lba > lastLba || blocks - 1 > lastLba - lba) return false;
    ++r.reads;
    return read(lba, blocks, dst);
  };
  auto header = [](const uint8_t *p) {
    return le32(p) == 0x20494645U && le32(p + 4) == 0x54524150U && le32(p + 8) == 0x10000 &&
           le32(p + 12) >= 92 && le32(p + 12) <= 4096 && !le32(p + 20) &&
           crc32(p, le32(p + 12), true) == le32(p + 16);
  };
  if (!fetch(1, 1, primary)) { r.error = "primary GPT read"; return r; }
  if (!header(primary)) { r.error = "primary GPT header CRC/revision"; return r; }
  r.primaryCrc = le32(primary + 16); r.entriesCrc = le32(primary + 88);
  r.entries = le32(primary + 80); r.entriesLba = le64(primary + 72);
  r.firstUsable = le64(primary + 40); r.lastUsable = le64(primary + 48);
  if (le64(primary + 24) != 1 || le64(primary + 32) != lastLba || !r.entries || r.entries > 128 ||
      le32(primary + 84) != 128 || r.entriesLba < 2 || r.entriesLba > 64) {
    r.error = "primary GPT geometry/capacity"; return r;
  }
  unsigned bytes = r.entries * 128, blocks = (bytes + 4095) / 4096;
  if (r.firstUsable < r.entriesLba + blocks || r.firstUsable > r.lastUsable ||
      r.lastUsable >= lastLba || lastLba - r.lastUsable <= blocks) {
    r.error = "GPT usable bounds"; return r;
  }
  if (!fetch(r.entriesLba, blocks, array)) { r.error = "primary array read"; return r; }
  if (crc32(array, bytes) != r.entriesCrc) { r.error = "primary array CRC"; return r; }
  for (unsigned i = 0; i < r.entries; ++i) {
    const uint8_t *p = array + i * 128;
    if (!used(p)) continue;
    ++r.used;
    uint64_t first = le64(p + 32), last = le64(p + 40);
    if (first < r.firstUsable || first > last || last > r.lastUsable) { r.error = "GPT entry bounds"; return r; }
    for (unsigned j = 0; j < i; ++j) {
      const uint8_t *other = array + j * 128;
      if (used(other) && first <= le64(other + 40) && le64(other + 32) <= last) { r.error = "GPT entry overlap"; return r; }
    }
  }
  if (!fetch(lastLba, 1, backup)) { r.error = "backup GPT read"; return r; }
  if (!header(backup)) { r.error = "backup GPT header CRC/revision"; return r; }
  r.backupCrc = le32(backup + 16); r.backupEntriesLba = le64(backup + 72);
  if (le64(backup + 24) != lastLba || le64(backup + 32) != 1 ||
      le64(backup + 40) != r.firstUsable || le64(backup + 48) != r.lastUsable ||
      le32(backup + 80) != r.entries || le32(backup + 84) != 128 || le32(backup + 88) != r.entriesCrc ||
      r.backupEntriesLba <= r.lastUsable || r.backupEntriesLba >= lastLba ||
      blocks > lastLba - r.backupEntriesLba) { r.error = "backup GPT geometry/mirror"; return r; }
  for (unsigned i = 56; i < 72; ++i)
    if (primary[i] != backup[i]) { r.error = "GPT disk GUID mismatch"; return r; }
  // Compare a block at a time, including CRC over exactly the logical entries
  // (padding need not agree between primary and backup arrays).
  for (unsigned block = 0; block < blocks; ++block) {
    if (!fetch(r.backupEntriesLba + block, 1, backup)) { r.error = "backup array read"; return r; }
    unsigned length = bytes - block * 4096;
    if (length > 4096) length = 4096;
    for (unsigned i = 0; i < length; ++i)
      if (backup[i] != array[block * 4096 + i]) { r.error = "GPT array mirror mismatch"; return r; }
  }
  return r;
}
}
