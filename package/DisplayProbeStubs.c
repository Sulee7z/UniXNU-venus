// Diagnostic-only stand-ins for board probes that the Venus display bring-up
// does not implement yet. They are empty by design and never touch hardware.
#include <stdint.h>
// native_keystore_probe is provided by KeyStoreProbe.cpp plus the selected
// AppleKeyStoreState component; native_hid_input_probe by HidInputProbe.cpp.
// No Venus touch/button producer is connected yet. Retain actual storage for
// the HID consumer's readable fields, and callable no-op registration hooks.
// Absolute-zero symbols are not callable ARM64 branch targets. These hooks
// neither retain nor invoke the callbacks, and never manufacture input events.
volatile uint32_t native_touch_seq, native_touch_count, native_touch_hid_reports;
volatile int native_touch_xs[12], native_touch_ys[12], native_touch_ids[12];
void native_touch_set_sink(void (*notify)(void *), void *context) {
    (void)notify; (void)context;
}
void native_buttons_set_sink(void (*notify)(void *, uint32_t), void *context) {
    (void)notify; (void)context;
}
void native_touch_probe(void) {}
void sheng_cpufreq_probe(void) {}
void sheng_wifi_probe(void) {}
void sheng_adsp_probe(void) {}
void sheng_battery_probe(void) {}
void sheng_audio_probe(void) {}
void sheng_buttons_probe(void) {}
void sheng_backlight_probe(void) {}
void sheng_dpu_probe(void) {}

// GPU scanout hand-off is not enabled in this display-only baseline. The
// Adreno publisher still calls this notification while closing a client.
void native_gop_gpu_drained_client_gone(void) {}
