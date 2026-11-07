#ifndef UNIXNU_RAM_DISK_STATUS_H
#define UNIXNU_RAM_DISK_STATUS_H

#define UNIXNU_RAM_DISK_STATUS_GUID \
  { 0xf6bcc315, 0xbe5e, 0x4ad7, { 0x8c, 0x26, 0x74, 0xd2, 0xc5, 0x52, 0x18, 0xa1 } }

typedef struct {
  UINT32 Version;
  CHAR8 Message[120];
} UNIXNU_RAM_DISK_STATUS;

#endif
