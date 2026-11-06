/* Software identity-only orientation consumer, distinct from transport.
 * No physical panel, scanout, sample, frame count, or CP object is simulated. */
#ifndef FX3_ORIENTATION_CORE_V1
#define FX3_ORIENTATION_CORE_V1
struct fo_mapping {unsigned width,height,hrev,vrev,osdrev,installed;unsigned long generation;};
struct fo_job {unsigned source,enumeration;unsigned long generation,transaction;};
struct fo_controller {unsigned ready,head,count;unsigned long generation,enqueued,consumed;struct fo_mapping display,input;struct fo_job queue[2];};
static void fo_init(struct fo_controller *c,unsigned w,unsigned h){__builtin_memset(c,0,sizeof *c);if(w==640&&h==480)c->ready=1;}
static int fo_enqueue(struct fo_controller *c,unsigned source,unsigned enumeration,unsigned long transaction){if(!c->ready||!source||!transaction||enumeration!=0||c->count==2||c->generation==~0UL||c->enqueued==~0UL)return -1;for(unsigned i=0;i<c->count;i++)if(c->queue[(c->head+i)%2].transaction==transaction)return -2;unsigned at=(c->head+c->count)%2;c->queue[at]=(struct fo_job){source,enumeration,c->generation+c->count+1,transaction};if(c->queue[at].generation<c->generation)return -1;c->count++;c->enqueued++;return 0;}
static int fo_map(const struct fo_mapping *m,unsigned long generation,unsigned x,unsigned y,unsigned *outx,unsigned *outy){if(!m->installed||m->width!=640||m->height!=480||m->generation!=generation||m->hrev||m->vrev||m->osdrev||x>=640||y>=480)return -1;*outx=x;*outy=y;return 0;}
/* Taking this job installs both live mapping descriptors before returning completion. */
static int fo_consume(struct fo_controller *c,struct fo_job *completion){if(!c->ready||!c->count)return -1;struct fo_job j=c->queue[c->head];if(j.enumeration||j.generation!=c->generation+1||c->consumed==~0UL)return -2;struct fo_mapping identity={640,480,0,0,0,1,j.generation};c->display=identity;c->input=identity;c->generation=j.generation;unsigned x,y;if(fo_map(&c->display,c->generation,639,479,&x,&y)||x!=639||y!=479||fo_map(&c->input,c->generation,639,479,&x,&y)||x!=639||y!=479)return -3;__builtin_memset(c->queue+c->head,0,sizeof c->queue[0]);c->head=(c->head+1)%2;c->count--;c->consumed++;*completion=j;return 0;}
#endif
