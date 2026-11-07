// SPDX-License-Identifier: MIT
#include "VenusStGeniTransport.h"
#include <string.h>

// Linux spi-geni-qcom.c: SPI_CS_DEASSERT opcode 9. The vendor STM driver
// keeps CS asserted for SPI_DELAY_CS after the final transfer. A delay after
// keep_cs=0 cannot satisfy that contract because CS has already risen.
static int release_cs(struct geni_spi *spi) {
    unsigned limit=spi->poll_limit?spi->poll_limit:20000;
    for(unsigned n=0;;++n) {
        if(!(spi->se.rd(spi->se.ctx,SE_GENI_STATUS)&GENI_STATUS_M_ACTIVE))break;
        if(n==limit)return GENI_ERR_TIMEOUT;
        spi->se.delay_us(spi->se.ctx,1);
    }
    spi->se.wr(spi->se.ctx,SE_GENI_M_IRQ_CLEAR,0xffffffffu);
    spi->se.wr(spi->se.ctx,SE_GENI_M_CMD0,9u<<GENI_M_OPCODE_SHIFT);
    for(unsigned n=0;n<limit;++n) {
        uint32_t irq=spi->se.rd(spi->se.ctx,SE_GENI_M_IRQ_STATUS);
        if(irq&(GENI_M_ERRORS|GENI_M_CMD_DONE)) {
            spi->se.wr(spi->se.ctx,SE_GENI_M_IRQ_CLEAR,irq);
            return (irq&GENI_M_ERRORS)?GENI_ERR_IO:0;
        }
        spi->se.delay_us(spi->se.ctx,1);
    }
    // Do not leave an unfinished CS command looking successful.
    spi->se.wr(spi->se.ctx,SE_GENI_M_CMD_CTRL_REG,GENI_M_CMD_ABORT);
    return GENI_ERR_TIMEOUT;
}
int vst_geni_message(struct geni_spi *spi,const uint8_t *command,size_t command_bytes,
                     uint8_t *out,size_t read_bytes,unsigned hold_us,int *cs_status) {
    if(cs_status)*cs_status=GENI_ERR_PARAM;
    if(!spi || !spi->se.rd || !spi->se.wr || !spi->se.delay_us ||
       !command || !command_bytes || command_bytes>272 || read_bytes>272-command_bytes ||
       (read_bytes&&!out) || hold_us>1000)return GENI_ERR_PARAM;
    uint8_t tx[272]={0},rx[272]={0};
    memcpy(tx,command,command_bytes);
    int status=geni_spi_transfer(spi,tx,read_bytes?rx:NULL,command_bytes+read_bytes,1);
    spi->se.delay_us(spi->se.ctx,hold_us);
    int ended=release_cs(spi);
    if(cs_status)*cs_status=ended;
    if(status)return status;
    if(ended)return ended;
    if(read_bytes)memcpy(out,rx+command_bytes,read_bytes);
    return 0;
}
