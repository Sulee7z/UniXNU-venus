// SPDX-License-Identifier: MIT
#include "VenusStGeniTransport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct mock {int transfer_error,release_error,busy,timeout;unsigned calls,phase,aborted;};
static uint32_t rd(void *context,uint32_t reg) {
    struct mock *m=context;
    if(reg==SE_GENI_STATUS)return m->busy?GENI_STATUS_M_ACTIVE:0;
    assert(reg==SE_GENI_M_IRQ_STATUS);
    if(m->timeout)return 0;
    return m->release_error?GENI_M_CMD_FAILURE:GENI_M_CMD_DONE;
}
static void wr(void *context,uint32_t reg,uint32_t value) {
    struct mock *m=context;
    if(reg==SE_GENI_M_CMD0){assert(m->phase==2 && value==(9u<<GENI_M_OPCODE_SHIFT));m->phase=3;}
    else if(reg==SE_GENI_M_CMD_CTRL_REG){assert(value==GENI_M_CMD_ABORT);m->aborted++;}
    else assert(reg==SE_GENI_M_IRQ_CLEAR);
}
static void delay(void *context,unsigned us){struct mock *m=context;if(us==10){assert(m->phase==1);m->phase=2;}else assert(us==1);}
int geni_spi_transfer(struct geni_spi *spi,const uint8_t *tx,uint8_t *rx,size_t len,int keep) {
    struct mock *m=spi->se.ctx;m->calls++;m->phase=1;
    assert(keep==1 && len==10 && tx[0]==0x87);
    for(unsigned i=1;i<len;++i)assert(tx[i]==0);
    memset(rx,0,len);rx[0]=0xca;rx[1]=0xff;rx[2]=0x13;rx[3]=0x01;
    return m->transfer_error;
}
int main(void) {
    struct mock m={0};struct geni_spi spi={0};spi.se=(struct geni_io){&m,rd,wr,delay};spi.poll_limit=3;
    uint8_t command=0x87,out[9];int cs=-1;
    assert(vst_geni_message(&spi,&command,1,out,9,10,&cs)==0 && cs==0 && m.phase==3);
    assert(out[0]==0xff && out[1]==0x13 && out[2]==1); // dummy retained for STM codec
    m=(struct mock){.transfer_error=GENI_ERR_IO};memset(out,0x5a,sizeof out);
    assert(vst_geni_message(&spi,&command,1,out,9,10,&cs)==GENI_ERR_IO && m.phase==3);
    for(unsigned i=0;i<9;++i)assert(out[i]==0x5a);
    m=(struct mock){.release_error=1};assert(vst_geni_message(&spi,&command,1,out,9,10,&cs)==GENI_ERR_IO && cs==GENI_ERR_IO);
    m=(struct mock){.timeout=1};assert(vst_geni_message(&spi,&command,1,out,9,10,&cs)==GENI_ERR_TIMEOUT && m.aborted==1);
    m=(struct mock){.busy=1};assert(vst_geni_message(&spi,&command,1,out,9,10,&cs)==GENI_ERR_TIMEOUT && m.phase==2);
    m=(struct mock){0};assert(vst_geni_message(&spi,&command,1,out,300,10,&cs)==GENI_ERR_PARAM && m.calls==0);
    puts("PASS: whole-message CS hold, dummy alignment, error propagation and bounded CS release");
    return 0;
}
