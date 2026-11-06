/* SPDX-License-Identifier:     GPL-2.0 */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
#ifndef __LDEC_DEBUG_H__
#define __LDEC_DEBUG_H__

#ifdef __cplusplus
extern "C" {
#endif

enum {
	LDEC_DEBUG_ERROR = 1,
	LDEC_DEBUG_TIME = LDEC_DEBUG_ERROR,
	LDEC_DEBUG_WARNING,
	LDEC_DEBUG_DEBUG,
	LDEC_DEBUG_INFO,
};

#ifndef DEBUG_PRINT

#define ldec_print( level, format, ...) do{} while(0)
#define LDEC_LOCK_TIMES_CHECK(e_time, s_time)

#else /* #ifndef DEBUG_PRINT */

#define LOG_PRIMASK     0x07

#define ldec_print( level, format, ...) do{ \
	if(( level & LOG_PRIMASK) <= LDEC_PRINT_LEVEL ){			\
		switch((level) & LOG_PRIMASK){                                      \
		case LDEC_DEBUG_ERROR:		printk("[LDEC ERR ] %s()[l %d] : " format,  __func__, __LINE__, ##__VA_ARGS__); break;	\
		case LDEC_DEBUG_WARNING:	printk("[LDEC WARN] %s()[l %d] : " format,  __func__, __LINE__, ##__VA_ARGS__); break;	\
		case LDEC_DEBUG_DEBUG:		printk("[LDEC DEB ] %s()[l %d] : " format,  __func__, __LINE__, ##__VA_ARGS__); break;	\
		case LDEC_DEBUG_INFO:		printk("[LDEC INFO] %s()[l %d] : " format,  __func__, __LINE__, ##__VA_ARGS__); break;	\
		default: break;	\
		};	\
	} \
} while(0)
 
#ifdef LDEC_LOCK_TIMES
#define LDEC_LOCK_TIMES_CHECK(e_time, s_time)	\
	do { \
		struct timespec64 ts = timespec64_sub(e_time,s_time);		\
		ldec_print(LDEC_DEBUG_TIME,"spin_lock_irqsave - spin_unlock_irqrestore execution time : %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec ); \
		if((ts.tv_nsec > 100000) || (ts.tv_sec > 0)){			\
			ldec_print(LDEC_DEBUG_TIME,"Over 100usec :: spin lock time %llu.%09lu [s]\n", ts.tv_sec,ts.tv_nsec ); \
		} else {							\
			ldec_print(LDEC_DEBUG_TIME,"Under 100usec :: spin lock time %llu.%09lu [s]\n", ts.tv_sec,ts.tv_nsec ); \
		}								\
	} while (0)
#else /* LOCKTIME */
#define LDEC_LOCK_TIMES_CHECK(e_time, s_time)
#endif /* LOCKTIME */

#endif /* #ifndef DEBUG_PRINT */
  

#ifdef __cplusplus 
}
#endif
#endif /* #ifndef _LDEC_DEBUG_H_ */
/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
