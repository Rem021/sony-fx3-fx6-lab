#include <stdio.h>
int ccmp_eq(int actual,int capacity,int flag);
int main(void){
    int actuals[]={0,1,4,5}; int caps[]={4}; int flags[]={0,1};
    for(int a=0;a<4;a++) for(int c=0;c<1;c++) for(int f=0;f<2;f++){
        int got=ccmp_eq(actuals[a],caps[c],flags[f]);
        printf("actual=%d cap=%d flag=%d b.eq=%d\n",actuals[a],caps[c],flags[f],got);
    }
    return 0;
}
