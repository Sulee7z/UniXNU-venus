  // Keep persistent Data entirely undiscoverable until the original
  // native_ram_block_volume_seed call after SystemOS has mounted.
  unsigned mode = &native_ufs_store_mode ? native_ufs_store_mode() : 0;
  if (mode) {
    if (isBig && mode != 2) return false;
    if (deferredData && deferredData != this) return false;
    deferredData = this;
    return true;
  }
  online = true;
  native_ram_block_ready = 1;
  registerService();
  return true;
