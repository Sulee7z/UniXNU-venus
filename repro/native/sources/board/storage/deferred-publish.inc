    if (online) return true;
    unsigned mode = &native_ufs_store_mode ? native_ufs_store_mode() : 0;
    if (!mode || (isBig && mode != 2)) return false;
    IOLog("DataUSB: restore enter mode=%u\n", mode);
    attachStore();
    IOLog("DataUSB: restore returned state=%u header=%u gpt=%u/%u loaded=%llu errors=%llu\n",
          native_data_persist_state, native_data_persist_header,
          native_data_persist_gpt, native_data_persist_gpt_after,
          native_data_persist_loaded, native_data_persist_errors);
    if (native_data_persist_gpt || native_data_persist_gpt_after ||
        (mode == 2 ? !direct : native_data_persist_state != 1 && native_data_persist_state != 6)) {
      IOLog("NativeRamBlock: store unavailable before publication (state=%u)\n", native_data_persist_state);
      return false;
    }
    online = true;
    native_ram_block_ready = 1;
    deferredData = nullptr;
    IOLog("DataUSB: media publication enter\n");
    registerService();
    IOLog("DataUSB: media publication returned\n");
    return true;
