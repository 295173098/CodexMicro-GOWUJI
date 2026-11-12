#pragma once
#include "pins.h"
#ifndef GOWUJI_HOST_SIM
#include <atomic>
#include <driver/gpio.h>
#include <driver/i2s_pdm.h>
#endif

namespace MicInput {
constexpr unsigned rate = 16000, samples = 160;
#ifdef GOWUJI_HOST_SIM
static bool active = false;
static uint32_t due = 0;
inline bool start() { active = true; due = millis()+10; return true; }
inline void stop() { active = false; }
inline size_t read(void *dst, size_t size) {
  if (!active || int32_t(millis()-due)<0) return 0;
  due += 10;
  memset(dst, 0x12, size);
  return size;
}
inline bool lost() { return false; }
#else
static i2s_chan_handle_t rx = nullptr;
static bool running = false;
static std::atomic<bool> overrun{false};
static bool IRAM_ATTR rxOverflow(i2s_chan_handle_t, i2s_event_data_t *, void *context) {
  static_cast<std::atomic<bool> *>(context)->store(true, std::memory_order_relaxed);
  return false;
}
inline void stop() {
  if (rx) {
    if (running) i2s_channel_disable(rx);
    i2s_del_channel(rx);
    rx = nullptr;
    running = false;
  }
  // Static clock puts the microphone in power down; don't load the reset strap.
  gpio_reset_pin(gpio_num_t(MIC_CLK_PIN));
  gpio_pullup_dis(gpio_num_t(MIC_CLK_PIN));
  gpio_set_level(gpio_num_t(MIC_CLK_PIN), 0);
  gpio_set_direction(gpio_num_t(MIC_CLK_PIN), GPIO_MODE_OUTPUT);
}
inline bool start() {
  i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
  channel.dma_desc_num = 4;
  channel.dma_frame_num = samples;
  if (i2s_new_channel(&channel, nullptr, &rx) != ESP_OK) return false;
  i2s_pdm_rx_config_t pdm{};
  pdm.clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(rate);
  pdm.clk_cfg.dn_sample_mode = I2S_PDM_DSR_16S;  // 2.048 MHz within ST's 1.2–3.25 MHz
  pdm.slot_cfg = I2S_PDM_RX_SLOT_PCM_FMT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  pdm.slot_cfg.slot_mask = I2S_PDM_SLOT_LEFT;  // LR tied low
  pdm.gpio_cfg.clk = gpio_num_t(MIC_CLK_PIN);
  pdm.gpio_cfg.din = gpio_num_t(MIC_DATA_PIN);
  i2s_event_callbacks_t callbacks{};
  callbacks.on_recv_q_ovf = rxOverflow;
  overrun.store(false, std::memory_order_relaxed);
  if (i2s_channel_init_pdm_rx_mode(rx,&pdm) != ESP_OK ||
      i2s_channel_register_event_callback(rx,&callbacks,&overrun) != ESP_OK ||
      i2s_channel_enable(rx) != ESP_OK) {
    stop();
    return false;
  }
  running = true;
  return true;
}
inline size_t read(void *dst, size_t size) {
  size_t got = 0;
  if (running) i2s_channel_read(rx,dst,size,&got,0);
  return got;
}
inline bool lost() { return overrun.load(std::memory_order_relaxed); }
#endif
}
