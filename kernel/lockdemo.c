#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"

#define LOCKTRACE_MAX 4096

enum locktrace_kind {
  LOCKTRACE_TRY = 1,
  LOCKTRACE_ACQ = 2,
  LOCKTRACE_REL = 3,
};

struct locktrace_event {
  uint64 seq;
  uint64 time;
  int cpu;
  int pid;
  int kind;
  int hold;
  char lock[16];
  char name[16];
};

static struct spinlock demo_lock;

static struct {
  struct spinlock lock;
  uint64 next_seq;
  uint64 tail_seq;
  struct locktrace_event ev[LOCKTRACE_MAX];
} tracebuf;

static char *
locktrace_kind_name(int kind)
{
  switch (kind) {
  case LOCKTRACE_TRY:
    return "try";
  case LOCKTRACE_ACQ:
    return "acq";
  case LOCKTRACE_REL:
    return "rel";
  default:
    return "???";
  }
}

static void
locktrace_emit(int kind, int hold)
{
  struct proc *p = myproc();
  struct locktrace_event *e;
  uint64 seq;

  if (p == 0)
    return;

  acquire(&tracebuf.lock);
  seq = tracebuf.next_seq;
  e = &tracebuf.ev[seq % LOCKTRACE_MAX];
  e->seq = seq;
  e->time = r_time();
  e->cpu = cpuid();
  e->pid = p->pid;
  e->kind = kind;
  e->hold = hold;
  safestrcpy(e->lock, demo_lock.name, sizeof(e->lock));
  safestrcpy(e->name, p->name, sizeof(e->name));
  tracebuf.next_seq = seq + 1;
  if (tracebuf.next_seq - tracebuf.tail_seq > LOCKTRACE_MAX)
    tracebuf.tail_seq = tracebuf.next_seq - LOCKTRACE_MAX;
  release(&tracebuf.lock);
}

void
locktraceinit(void)
{
  initlock(&tracebuf.lock, "locktrace");
  tracebuf.next_seq = 0;
  tracebuf.tail_seq = 0;
  initlock(&demo_lock, "vizlock");
}

uint64
sys_lockdemo(void)
{
  int hold;
  uint64 deadline;

  argint(0, &hold);
  if (hold < 1)
    hold = 1;
  if (hold > 100000000)
    hold = 100000000;

  locktrace_emit(LOCKTRACE_TRY, hold);
  acquire(&demo_lock);
  locktrace_emit(LOCKTRACE_ACQ, hold);
  deadline = r_time() + (uint64)hold;
  while (r_time() < deadline)
    ;
  locktrace_emit(LOCKTRACE_REL, hold);
  release(&demo_lock);

  return 0;
}

uint64
sys_locktrace(void)
{
  uint64 start;
  uint64 end;
  uint64 seq;
  struct locktrace_event *e;

  acquire(&tracebuf.lock);
  start = tracebuf.tail_seq;
  end = tracebuf.next_seq;
  printk("BEGIN LOCKTRACE %lu\n", end);
  for (seq = start; seq < end; seq++) {
    e = &tracebuf.ev[seq % LOCKTRACE_MAX];
    printk("EVENT seq=%lu time=%lu cpu=%d pid=%d kind=%s hold=%d lock=%s name=%s\n",
           e->seq, e->time, e->cpu, e->pid, locktrace_kind_name(e->kind),
           e->hold, e->lock, e->name);
  }
  printk("END LOCKTRACE %lu\n", end);
  tracebuf.tail_seq = end;
  release(&tracebuf.lock);

  return 0;
}
