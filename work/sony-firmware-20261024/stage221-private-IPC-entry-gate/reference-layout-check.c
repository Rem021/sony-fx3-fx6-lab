#define __user
typedef unsigned long __kernel_size_t;
struct iovec;
struct user_msghdr {
	void		__user *msg_name;	/* ptr to socket address structure */
	int		msg_namelen;		/* size of socket address structure */
	struct iovec	__user *msg_iov;	/* scatter/gather array */
	__kernel_size_t	msg_iovlen;		/* # elements in msg_iov */
	void		__user *msg_control;	/* ancillary data */
	__kernel_size_t	msg_controllen;		/* ancillary data buffer length */
	unsigned int	msg_flags;		/* flags on received message */
};

_Static_assert(sizeof(void*)==8 && sizeof(unsigned long)==8,"native ARM64");
_Static_assert(sizeof(struct user_msghdr)==56,"reference header size");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_name)==0,"name");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_namelen)==8,"namelen");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_iov)==16,"iov");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_iovlen)==24,"iovlen");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_control)==32,"control");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_controllen)==40,"controllen");
_Static_assert(__builtin_offsetof(struct user_msghdr,msg_flags)==48,"flags");
