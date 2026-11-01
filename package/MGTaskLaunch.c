// SPDX-License-Identifier: MIT
// Runs as launchd's existing prng_seedctl early boot task. Parent immediately
// execs the byte-identical original. One orphan supervisor measures in a mobile
// child with the inherited launchd bootstrap context; bounded wait/kill/reap.
#ifdef MG_TASK_HOST_TEST
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <grp.h>
#include <stdio.h>
#include <errno.h>
#define task_errno() errno
#else
#include <stdint.h>
extern int open(const char *,int,...),close(int),fcntl(int,int,...),dprintf(int,const char *,...);
extern int getpid(void),fork(void),execve(const char *,char *const[],char *const[]);
extern unsigned getuid(void),sleep(unsigned);
extern int setgroups(int,const unsigned *),setgid(unsigned),setuid(unsigned),dup2(int,int),fsync(int);
extern int waitpid(int,int *,int),kill(int,int),*__error(void);
extern void _exit(int);
#define task_errno() (*__error())
#define O_WRONLY 1
#define O_CREAT 0x200
#define O_EXCL 0x800
#define O_NOFOLLOW 0x100
#define F_SETFD 2
#define F_DUPFD 0
#define FD_CLOEXEC 1
#define WNOHANG 1
#define SIGKILL 9
#define EINTR 4
#endif
extern char **environ;
#ifndef MG_TASK_ORIGINAL
#define MG_TASK_ORIGINAL "/private/var/ngpu/original/prng_seedctl"
#define MG_TASK_QUERY "/private/var/ngpu/bin/venus-mg-query"
#define MG_TASK_LOG "/private/var/tmp/venus-mg-query-009-launch.jsonl"
#define MG_TASK_STDOUT "/private/var/tmp/venus-mg-query-009.json"
#define MG_TASK_STDERR "/private/var/tmp/venus-mg-query-009.stderr"
#endif
#ifndef MG_TASK_DELAY
#define MG_TASK_DELAY 5
#endif
#ifndef MG_TASK_TIMEOUT
#define MG_TASK_TIMEOUT 30
#endif

static void event(int log,const char *name,int value) {
    if(log>=0){dprintf(log,"{\"probe\":\"venus-mg-task-v1\",\"event\":\"%s\",\"pid\":%d,\"value\":%d}\n",name,getpid(),value);fsync(log);}
}

static void worker(int log) {
    if(setgroups(0,0)||setgid(501)||setuid(501)){event(log,"identity_failed",task_errno());_exit(120);}
    int err=open(MG_TASK_STDERR,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(err<0){event(log,"stderr_open_failed",task_errno());_exit(121);}
    int out=open(MG_TASK_STDOUT,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(out<0){event(log,"stdout_open_failed",task_errno());close(err);_exit(122);}
    if(dup2(out,1)<0||dup2(err,2)<0){event(log,"redirect_failed",task_errno());_exit(123);}
    if(out>2)close(out);if(err>2)close(err);
    event(log,"query_exec",(int)getuid());
    char *args[]={MG_TASK_QUERY,0};execve(MG_TASK_QUERY,args,environ);
    int error=task_errno();event(log,"query_exec_failed",error);
    dprintf(2,"MG query exec failed: %d\n",error);fsync(2);_exit(124);
}

static void supervise(int log) {
    // Do not hold the early boot task's stdio pipes after its parent exits.
    close(0);close(1);close(2);
    int null=open("/dev/null",O_WRONLY|O_NOFOLLOW);
    if(null!=0||dup2(null,1)<0||dup2(null,2)<0){event(log,"stdio_detach_failed",task_errno());_exit(119);}
    event(log,"supervisor_started",MG_TASK_DELAY);
    unsigned remaining=MG_TASK_DELAY;while(remaining)remaining=sleep(remaining);
    int pid=fork();if(pid<0){event(log,"worker_fork_failed",task_errno());_exit(125);}
    if(!pid)worker(log);
    int status=0,done=0;
    for(unsigned i=0;i<MG_TASK_TIMEOUT;++i){
        int result=waitpid(pid,&status,WNOHANG);
        if(result==pid){done=1;break;}
        if(result<0&&task_errno()!=EINTR){event(log,"wait_failed",task_errno());_exit(126);}
        sleep(1);
    }
    if(!done){event(log,"query_timeout",pid);kill(pid,SIGKILL);while(waitpid(pid,&status,0)<0&&task_errno()==EINTR){} }
    event(log,"query_wait_status",status);
    // Sync successful or partial output without interpreting absent bytes as0.
    const char *paths[]={MG_TASK_STDOUT,MG_TASK_STDERR};
    for(unsigned i=0;i<2;++i){int fd=open(paths[i],O_WRONLY|O_NOFOLLOW);if(fd>=0){fsync(fd);close(fd);}}
    event(log,"supervisor_finished",done);if(log>=0)close(log);_exit(0);
}

int main(int argc,char **argv) {
    (void)argc;
    int log=-1;
    if(getuid()==0&&getpid()!=1){
        log=open(MG_TASK_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
        if(log>=0&&log<3){int saved=fcntl(log,F_DUPFD,3);close(log);log=saved;}
        if(log>=0){
            fcntl(log,F_SETFD,FD_CLOEXEC);event(log,"task_started",0);
            int pid=fork();
            if(!pid)supervise(log);
            event(log,pid<0?"supervisor_fork_failed":"supervisor_forked",pid<0?task_errno():pid);
        }
    }
    event(log,"original_exec",0);
    execve(MG_TASK_ORIGINAL,argv,environ);
    event(log,"original_exec_failed",task_errno());if(log>=0)close(log);return 127;
}
