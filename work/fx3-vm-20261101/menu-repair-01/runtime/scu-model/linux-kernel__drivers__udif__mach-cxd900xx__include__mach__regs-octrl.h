/*
 * mach-cxd900xx/include/mach/regs-octrl.h
 *
 * CXD90057 OCTRL registers
 *
 * Copyright 2018,2019 Sony Imaging Products & Solutions Inc
 *
 *  This program is free software; you can redistribute  it and/or modify it
 *  under  the terms of  the GNU General  Public License as published by the
 *  Free Software Foundation;  version 2 of the  License.
 *
 *  THIS  SOFTWARE  IS PROVIDED   ``AS  IS'' AND   ANY  EXPRESS OR IMPLIED
 *  WARRANTIES,   INCLUDING, BUT NOT  LIMITED  TO, THE IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
 *  NO  EVENT  SHALL   THE AUTHOR  BE    LIABLE FOR ANY   DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED   TO, PROCUREMENT OF  SUBSTITUTE GOODS  OR SERVICES; LOSS OF
 *  USE, DATA,  OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
 *  ANY THEORY OF LIABILITY, WHETHER IN  CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 *  You should have received a copy of the  GNU General Public License along
 *  with this program; if not, write  to the Free Software Foundation, Inc.,
 *  51 Franklin Street, Suite 500, Boston, MA 02110-1335, USA.
 *
 */
#ifndef __REGS_OCTRL_H
#define __REGS_OCTRL_H

#include <mach/regs-scu.h>
#define OCTRL_DATA		SCU_DATA
#define OCTRL_SET		SCU_SET
#define OCTRL_CLR		SCU_CLR

#define OCTRL_DS0		(0x400)
#define OCTRL_DS1		(0x4e0)
#define OCTRL_DS2		(0x5c0)
#define OCTRL_DS3		(0x6a0)
#define OCTRL_PULL		(0x780)
#define OCTRL_PUP		(0x8b0)
#define OCTRL_SCHT		(0x9e0)
#define OCTRL_MSEL		(0xb10)
#define OCTRL_SLEW		(0xb20)
#define OCTRL_OEN		(0xb40)

#endif /* __REGS_OCTRL_H */
