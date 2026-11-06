/* Explicit virtual-panel-config only. No framebuffer writes or CP driver calls. */
#ifndef FX3_PANEL_CONFIG_CORE_V1
#define FX3_PANEL_CONFIG_CORE_V1
struct vp_job {unsigned source,enumeration;unsigned long transaction,generation;};
struct vp_panel {unsigned ready,head,count,applied,hrev,vrev,osd_rev,control,tp_axes_reversed;unsigned long generation,enqueued,consumed,readbacks;struct vp_job queue[2];};
static void vp_init(struct vp_panel *p){__builtin_memset(p,0,sizeof *p);p->ready=1;}
static int vp_enqueue(struct vp_panel *p,unsigned source,unsigned enumeration,unsigned long transaction){if(!p->ready||!source||enumeration!=2||!transaction||p->count==2||p->generation>~0UL-(p->count+1UL)||p->enqueued==~0UL)return -1;for(unsigned i=0;i<p->count;i++)if(p->queue[(p->head+i)%2].transaction==transaction)return -2;p->queue[(p->head+p->count)%2]=(struct vp_job){source,enumeration,transaction,p->generation+p->count+1};p->count++;p->enqueued++;return 0;}
/* Separate software consumer: install all properties, then read back before completion. */
static int vp_readback(struct vp_panel *p,unsigned long generation,unsigned *control,unsigned *osd){if(!p->ready||!p->applied||p->generation!=generation||p->hrev!=1||p->vrev!=1||p->osd_rev||p->control!=3||p->tp_axes_reversed!=1)return -1;*control=p->control;*osd=p->osd_rev;return 0;}
static int vp_consume(struct vp_panel *p,struct vp_job *done){if(!p->ready||!p->count||p->consumed==~0UL||p->readbacks==~0UL)return -1;struct vp_job j=p->queue[p->head];if(j.enumeration!=2||j.generation!=p->generation+1)return -2;p->hrev=p->vrev=1;p->osd_rev=0;p->control=2*p->hrev+p->vrev;p->tp_axes_reversed=1;p->generation=j.generation;p->applied=1;unsigned c,o;if(vp_readback(p,j.generation,&c,&o)||c!=3||o)return -3;p->readbacks++;p->consumed++;__builtin_memset(p->queue+p->head,0,sizeof p->queue[0]);p->head=(p->head+1)%2;p->count--;*done=j;return 0;}
#endif
