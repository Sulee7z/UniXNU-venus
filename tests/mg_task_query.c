// Host exec/fork contract fixture; no claim of actual MG answers.
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void){
    const char *mode=getenv("MG_TEST_MODE");
    if(mode&&strcmp(mode,"timeout")==0){sleep(15);return 0;}
    dprintf(1,"{\"uid\":%u,\"gid\":%u,\"environment\":\"%s\",\"complete\":true}\n",
            getuid(),getgid(),getenv("MG_TEST_CONTEXT"));
    return 0;
}
