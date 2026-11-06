#ifndef FX3_IDLE_HELD_CLASSIFIER_H
#define FX3_IDLE_HELD_CLASSIFIER_H
#include "service_flow.h"
enum {
    FX3_IDLE_MISSING=1u, FX3_IDLE_NOT_HELD=2u, FX3_IDLE_PENDING=4u,
    FX3_IDLE_ROUTE=8u, FX3_IDLE_MSC=16u, FX3_IDLE_SERVICE=32u,
    FX3_IDLE_JOURNAL=64u, FX3_IDLE_OWNER=128u
};
/* Pure classification of the flow's own objects after owner_core returns.
 * Zero does NOT prove native-owner pointers are empty, permit process exit,
 * release a guard, or establish that camera threads/mode have recovered. */
unsigned fx3_idle_held_flow_reasons(const fx3_service_flow *);
#endif
