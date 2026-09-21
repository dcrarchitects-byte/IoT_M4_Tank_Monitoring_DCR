// Wokwi Custom Chip - BME280 Environmental Sensor
// SPDX-License-Identifier: MIT
// Base model adapted from the BME280 custom-chip example by Shaktijeet Mahapatra.

#include "wokwi-api.h"
#include <stdio.h>
#include <stdlib.h>

#define BME280_REG_ID        0xD0
#define BME280_CHIP_ID_VALUE 0x60
#define BME280_REG_TEMP      0xFA
#define BME280_REG_PRESS     0xF7
#define BME280_REG_HUMID     0xFD

typedef struct {
    pin_t pin_scl;
    pin_t pin_sda;
    uint32_t attr_temp;
    uint32_t attr_humid;
    uint32_t attr_press;
    uint8_t current_register;
    bool address_received;
} chip_state_t;

static bool chip_i2c_connect(void *user_data, uint32_t address, bool is_write) {
    chip_state_t *chip = (chip_state_t*)user_data;
    chip->address_received = false;
    return true;
}

static bool chip_i2c_write(void *user_data, uint8_t data) {
    chip_state_t *chip = (chip_state_t*)user_data;
    if (!chip->address_received) {
        chip->current_register = data;
        chip->address_received = true;
    } else {
        chip->current_register++;
    }
    return true;
}

static uint8_t chip_i2c_read(void *user_data) {
    chip_state_t *chip = (chip_state_t*)user_data;
    uint8_t result = 0x00;

    switch (chip->current_register) {
        case BME280_REG_ID:
            result = BME280_CHIP_ID_VALUE;
            break;
        case BME280_REG_TEMP:
            result = (uint8_t)attr_read(chip->attr_temp);
            break;
        case BME280_REG_HUMID:
            result = (uint8_t)attr_read(chip->attr_humid);
            break;
        case BME280_REG_PRESS:
            result = (uint8_t)(attr_read(chip->attr_press) / 4);
            break;
        default:
            result = 0x00;
            break;
    }

    chip->current_register++;
    return result;
}

static void chip_i2c_disconnect(void *user_data) {
    (void)user_data;
}

void chip_init(void) {
    chip_state_t *chip = malloc(sizeof(chip_state_t));

    chip->pin_scl = pin_init("SCL", INPUT);
    chip->pin_sda = pin_init("SDA", INPUT);

    const i2c_config_t config = {
        .address = 0x76,
        .scl = chip->pin_scl,
        .sda = chip->pin_sda,
        .connect = chip_i2c_connect,
        .read = chip_i2c_read,
        .write = chip_i2c_write,
        .disconnect = chip_i2c_disconnect,
        .user_data = chip
    };

    i2c_init(&config);

    chip->attr_temp = attr_init("temperature", 25);
    chip->attr_humid = attr_init("humidity", 50);
    chip->attr_press = attr_init("pressure", 1013);
}
