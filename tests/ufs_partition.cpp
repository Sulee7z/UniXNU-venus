// SPDX-License-Identifier: BSD-2-Clause-Patent
// Reuse the actual transport's GPT fixture and parser with each selected name.
#define main upstream_layout_main
#include "RootLayout.cpp"
#undef main

static bool selects(const char *name)
{
  fixture();
  memset(entries + 56, 0, 72);
  assert(strlen(name) < 36);
  for (unsigned i = 0; i < strlen(name); ++i) entries[56 + 2 * i] = name[i];
  checksums();
  RootLayout layout;
  const char *why = nullptr;
  return findRootLayout(&layout, &why);
}

int main()
{
  const char *wanted = NATIVE_UFS_ROOT_PARTITION;
  assert(selects(wanted));
  assert(!selects(strcmp(wanted, "unixnu") ? "unixnu" : "userdata"));
  assert(!selects("unixnu-extra"));
  assert(!selects("userdata-extra"));
  puts("PASS: exact selected GPT partition; other target and prefix matches rejected");
}
