# An Intel 8080 emulator

import urllib.request
import ssl
import sys
import time

mem = [0]*65536
regs = [0]*9
pc = 0
sp = 0

FLAG=8

CARRY_BIT=0b00000001
PARITY_BIT=0b00000100
AUX_CARRY_BIT=0b00010000
ZERO_BIT=0b01000000
SIGN_BIT=0b10000000

half_carry_table=[0, 0, 1, 0, 1, 0, 1, 1]
sub_half_carry_table=[0, 1, 1, 1, 0, 0, 0, 1]


def LoadHex():
	hex="""
:1004000078047804000000000000000000000000F4
:1004100000000000000000000000000000000000DC
:1004200000000000000000000000000000000000CC
:1004300000000000000000000000000000000000BC
:1004400000000000000000000000000000000000AC
:10045000000000000000000000000000000000009C
:10046000000000000000000000000000000000008C
:08047000000000000000000084
:10001000213704237DFE78CA1C010E01E5CD0500C1
:10002000E177FE0AC21300213804CD3000C313006B
:100030007EFE0AC8CDFF0047E5D178FE22C24C0003
:100040007E23FE0ACA2101FE22C23A007ECDFF00B5
:10005000B8C2580023C33A002B7EF680772378FE7F
:1000600020CA3000FE30CAA000FE41C274007D3DAF
:10007000BBCA8E00CDCD00FEECCA8900E52A020481
:100080007723220204E1C330003E00C321011AE6B7
:1000900080DE412A02047723220204EB23C33000CE
:1000A000210000E5C1292909291AE67FD6304F062B
:1000B00000091A13E680CAA300D5EB2A02043E1AEF
:1000C000772373237223220204E1C33000E5217EEB
:1000D000032C2C7DFEEBCAED00D5CDF100D1FE0046
:1000E000CAED007E2CE680C2D100C3E3007D3CE176
:1000F000C91A96C07EE680EE80C81323C3F100FEC5
:1001000030DA0901FE3ADA1401FE41DA1301FE5B2E
:10011000DA1701C93E30C93E41C9C9C93E0FC322E1
:1001200001E1FE0AC22901C607C630F53E0ACD42EA
:10013000013E45CD4201F1CD42013E0ACD4201C30F
:0801400010005F0E02C3050070
:100380005052494ED41A014C45D41B01474F54CF0B
:100390000000474F5355C200005245545552CE00FD
:1003A0000049C60000454EC40000544845CE000038
:1003B0005255CE00004C4953D40000434C4541D225
:1003C0000000AC0000AB0000AD0000AA0000AF00D0
:1003D00000BD0000BE0000BC0000BE00003CBD002F
:0C03E000003EBD0000A80000A9000000C5
:00000001FF
"""
	
	state=0
	str=""
	for c in hex:
		print(c)
		if c==":":
			state=1
			str=""
		else:
			str+=c
			if state==1 and len(str)==2:
				recordlen=int(str,16)
				str=""
				state=2
			elif state==2 and len(str)==4:
				addr=int(str,16)
				str=""
				state=3
			elif state==3 and len(str)==2:
				str=""
				state=4
			elif state==4 and recordlen>0 and len(str)==2:
				recordlen-=1
				print(str)
				mem[addr]=int(str,16)
				addr+=1
				str=""
			

def LoadFile():
	unverified_context = ssl._create_unverified_context()
	url="https://altairclone.com/downloads/cpu_tests/8080EXER.COM"
	#url="https://altairclone.com/downloads/cpu_tests/8080PRE.COM"
	#url="https://altairclone.com/downloads/cpu_tests/TST8080.COM"

	addr=0x100

	file = urllib.request.urlopen(url,context=unverified_context)

	byte=file.read(1)
	while byte:
		mem[addr]=int.from_bytes(byte,"little")
		byte=file.read(1)
		addr+=1

def LoadAscFile(f):
	with open(f, 'r') as file:
		sections = eval(file.read())
	for (addr,b) in sections:
		for x in b:
			mem[addr]=x
			addr+=1


def NOP(i):
	global pc
	pc+=1
	
InstFuncs=[NOP]*256

def SetInstFuncs(l,u,s,f):
	while l<=u:
		InstFuncs[l]=f
		l+=s

def SetCarry(b):
	if b:
		regs[FLAG]|=CARRY_BIT
	else:
		regs[FLAG]&=(CARRY_BIT^0b11111111)

def SetAuxCarry(b):
	if b:
		regs[FLAG]|=AUX_CARRY_BIT
	else:
		regs[FLAG]&=(AUX_CARRY_BIT^0b11111111)

def SetParity(x):
	y=((x&0b11110000)>>4)^(x&0b00001111)
	y=((y&0b00000011)<<2)^(y&0b00001100)
	y=((y&0b00001000)>>1)^(y&0b00000100)
	
	regs[FLAG]=(regs[FLAG]&(PARITY_BIT^0b11111111))|(y^PARITY_BIT)

def SetZeroSign(x):
	if x==0:
		regs[FLAG]|=ZERO_BIT
	else:
		regs[FLAG]&=(ZERO_BIT^0b11111111)
		
	if x>=128:
		regs[FLAG]|=SIGN_BIT
	else:
		regs[FLAG]&=(SIGN_BIT^0b11111111)

def CarryBit(i):
	global pc
	
	if i&0b00001000==0:
		regs[FLAG]|=CARRY_BIT
	else:
		regs[FLAG]=regs[FLAG]^CARRY_BIT
	pc+=1
	
def Inr(i):
	global pc
	
	r=(i&0b00111000)>>3
	
	regs[r]=(regs[r]+1)&0b11111111
		
	SetAuxCarry(regs[r]&0b00001111==0)
	SetZeroSign(regs[r])
	SetParity(regs[r])
		
	pc+=1

def Dcr(i):
	global pc
	
	r=(i&0b00111000)>>3
	
	regs[r]=(regs[r]+255)&0b11111111
		
	SetAuxCarry(not regs[r]&0b00001111==0b00001111)
	SetZeroSign(regs[r])
	SetParity(regs[r])
		
	pc+=1

def Cma(i):
	global pc
	
	regs[7]^=0b11111111
		
	pc+=1
	
def Daa(i):
	global pc
	
	l4=regs[7]&0x0f
		
	if l4>9 or regs[FLAG]&AUX_CARRY_BIT!=0:
		l4+=0x06
		regs[7]+=0x06
		
	SetAuxCarry(l4>=16)

	if (regs[7]>>4)>9 or regs[FLAG]&CARRY_BIT!=0:
		regs[7]+=0x60
		SetCarry(True)
		
	regs[7]&=0b11111111
	
	SetZeroSign(regs[7])
	SetParity(regs[7])        
	
	pc+=1
	
def Mov(i):
	global pc
	
	dst=(i&0b00111000)>>3
	src=i&0b00000111
	
	regs[dst]=regs[src]
	
	pc+=1
	
def Stax(i):
	global pc
	
	r=(i&0b00010000)>>3
	
	mem[(regs[r]<<8)+regs[r+1]]=regs[7]
	
	pc+=1


def Ldax(i):
	global pc
	
	r=(i&0b00010000)>>3
	
	regs[7]=mem[(regs[r]<<8)+regs[r+1]]
	
	pc+=1
	
	
def Mvi(i):
	global pc
	
	r=(i&0b00111000)>>3
	
	pc+=1
	
	regs[r]=mem[pc]
	
	pc+=1

def Adi(i):
	global pc
	
	src=mem[pc+1]
	
	index=(regs[7]&0b00001000)>>1
	index+=(src&0b00001000)>>2

	regs[7]+=src
		
	index+=(regs[7]&0b00001000)>>3
	SetAuxCarry(half_carry_table[index]==1)
	SetCarry(regs[7]>=256)
		
	regs[7]&=0b11111111
	
	SetZeroSign(regs[7])
	SetParity(regs[7])
		
	pc+=2
	
def OpAcc(i):
	global pc
	
	if i&0b01000000==0:
		op=(i&0b00111000)>>3
		r=i&0b00000111
		src=regs[r]
	else:
		op=(i&0b00111000)>>3
		src=mem[pc+1]
		pc+=1
	
	if op==0 or op==1:
		index=(regs[7]&0b00001000)>>1
		index+=(src&0b00001000)>>2
		if op==1 and (regs[FLAG]&CARRY_BIT != 0):
			regs[7]+=1
		regs[7]+=src
		
		index+=(regs[7]&0b00001000)>>3
		SetAuxCarry(half_carry_table[index]==1)
		SetCarry(regs[7]>=256)
		
	if op==2 or op==3 or op==7:
		tmp=regs[7]
		index=(regs[7]&0b00001000)>>1
		index+=(src&0b00001000)>>2
		regs[7]+=(src^0b11111111)
		if not(op==3 and (regs[FLAG]&CARRY_BIT != 0)):
			regs[7]+=1

		index+=(regs[7]&0b00001000)>>3
		SetAuxCarry(sub_half_carry_table[index]==0)
		SetCarry(regs[7]<256)
	
	if op==4:
		SetAuxCarry(((regs[7]|src) & 0x08) != 0)
		regs[7]&=src
		SetCarry(False)
	
	if op==5:
		regs[7]^=src
		SetCarry(False)
		SetAuxCarry(False)
		
	if op==6:
		regs[7]|=src
		SetCarry(False)
		SetAuxCarry(False)
		
	regs[7]&=0b11111111
	
	SetZeroSign(regs[7])
	SetParity(regs[7])
	
	if op==7:
		regs[7]=tmp
		
	pc+=1

def Rlc(i):
	global pc
	regs[7]=regs[7]<<1
	regs[7]|=(regs[7]&0b100000000)>>8
	SetCarry((regs[7]&1)!=0)
	regs[7]=regs[7]&0b11111111
	pc+=1

def Rrc(i):
	global pc
	SetCarry((regs[7]&1)!=0)
	regs[7]=(regs[7]>>1)|((regs[7]&1)<<7)
	pc+=1
	
def Ral(i):
	global pc
	regs[7]=regs[7]<<1
	regs[7]|=1 if regs[FLAG]&CARRY_BIT != 0 else 0
	SetCarry((regs[7]&0b100000000)!=0)
	regs[7]=regs[7]&0b11111111
	pc+=1

def Rar(i):
	global pc
	c=(regs[7]&1)!=0
	regs[7]=regs[7]>>1
	regs[7]|=0x80 if regs[FLAG]&CARRY_BIT != 0 else 0
	SetCarry(c)
	pc+=1

def Push(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4

	if rp<3:
		mem[sp-1]=regs[rp*2]
		mem[sp-2]=regs[rp*2+1]
	else:
		mem[sp-1]=regs[7]
		mem[sp-2]=regs[FLAG]|0x02
	sp=(sp+0xfffe)&0xffff

	pc+=1

def Pop(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4
	if rp<3:
		regs[rp*2]=mem[sp+1]
		regs[rp*2+1]=mem[sp]
	else:
		regs[7]=mem[sp+1]
		regs[FLAG]=mem[sp]
	sp=(sp+2)&0xffff

	pc+=1

def Dad(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4

	if rp<3:
		result = (regs[4]<<8)+regs[5]+(regs[rp*2]<<8)+regs[rp*2+1]
	else:
		result = (regs[4]<<8)+regs[5]+sp

	regs[4]=(result&0xff00)>>8
	regs[5]=result&0xff

	SetCarry(result&0x10000!=0)

	pc+=1

def Inx(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4

	if rp<3:
		regs[rp*2+1] = (regs[rp*2+1]+1)&0xff
		if regs[rp*2+1]==0:
			regs[rp*2] = (regs[rp*2]+1)&0xff
	else:
		sp = (sp+1)&0xffff

	pc+=1

def Dcx(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4

	if rp<3:
		regs[rp*2+1] = (regs[rp*2+1]+0xff)&0xff
		if regs[rp*2+1]==0xff:
			regs[rp*2] = (regs[rp*2]+0xff)&0xff
	else:
		sp = (sp+0xffff)&0xffff

	pc+=1

def Xchg(i):
	global pc
	regs[2],regs[3],regs[4],regs[5]=regs[4],regs[5],regs[2],regs[3]

	pc+=1

def Xthl(i):
	global pc
	regs[4],regs[5],mem[sp+1],mem[sp]=mem[sp+1],mem[sp],regs[4],regs[5]

	pc+=1

def Sphl(i):
	global pc
	global sp
	sp=(regs[4]<<8)+regs[5]

	pc+=1

def Lxi(i):
	global pc
	global sp
	rp=(i&0b00110000)>>4

	if rp<3:
		regs[rp*2+1] = mem[pc+1]
		regs[rp*2] = mem[pc+2]
	else:
		sp = (mem[pc+2]<<8)+mem[pc+1]

	pc+=3

def Sta(i):
	global pc
	mem[(mem[pc+2]<<8)+mem[pc+1]]=regs[7]
	pc+=3

def Lda(i):
	global pc
	regs[7]=mem[(mem[pc+2]<<8)+mem[pc+1]]
	pc+=3

def Shld(i):
	global pc
	mem[(mem[pc+2]<<8)+mem[pc+1]]=regs[5]
	mem[((mem[pc+2]<<8)+mem[pc+1]+1)&0xffff]=regs[4]
	pc+=3

def Lhld(i):
	global pc
	regs[5]=mem[(mem[pc+2]<<8)+mem[pc+1]]
	regs[4]=mem[((mem[pc+2]<<8)+mem[pc+1]+1)&0xffff]
	pc+=3
	
def Pchl(i):
	global pc
	pc=(regs[4]<<8)+regs[5]

def Jnz(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&ZERO_BIT==0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jz(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&ZERO_BIT!=0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jnc(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&CARRY_BIT==0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jc(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&CARRY_BIT!=0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)
	
def Jp(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&SIGN_BIT==0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jm(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&SIGN_BIT!=0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jpe(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&PARITY_BIT!=0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)

def Jpo(i):
	global pc
	global sp
	pc+=3
	if regs[FLAG]&PARITY_BIT==0:
		if i&0b00000100!=0: # is it a call?
			mem[sp-1]=(pc>>8)
			mem[sp-2]=pc&0xff
			sp=(sp+0xfffe)&0xffff
		pc=mem[pc-2]+(mem[pc-1]<<8)
		
def Jmp(i):
	global pc
	global sp
	pc+=3
	if i&0b00000100!=0: # is it a call?
		mem[sp-1]=(pc>>8)&0xff
		mem[sp-2]=pc&0xff
		sp=(sp+0xfffe)&0xffff
	pc=mem[pc-2]+(mem[pc-1]<<8)
	
def Rnz(i):
	global pc
	global sp
	if regs[FLAG]&ZERO_BIT==0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rz(i):
	global pc
	global sp
	if regs[FLAG]&ZERO_BIT!=0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rnc(i):
	global pc
	global sp
	if regs[FLAG]&CARRY_BIT==0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rc(i):
	global pc
	global sp
	if regs[FLAG]&CARRY_BIT!=0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1
	
def Rp(i):
	global pc
	global sp
	if regs[FLAG]&SIGN_BIT==0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rm(i):
	global pc
	global sp
	if regs[FLAG]&SIGN_BIT!=0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rpe(i):
	global pc
	global sp
	if regs[FLAG]&PARITY_BIT!=0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1

def Rpo(i):
	global pc
	global sp
	if regs[FLAG]&PARITY_BIT==0:
		pc=mem[sp]+(mem[sp+1]<<8)
		sp=(sp+2)&0xffff
	else:
		pc+=1
		
def Ret(i):
	global pc
	global sp
	pc=mem[sp]+(mem[sp+1]<<8)
	sp=(sp+2)&0xffff

def Rst(i):
	global pc
	global sp
	pc+=1
	mem[sp-1]=(pc>>8)&0xff
	mem[sp-2]=pc&0xff
	sp=(sp+0xfffe)&0xffff
	pc=i&0b00111000
	
def Out(i):
	global pc
	pc+=1
	o=mem[pc]
	
	if o==0:
		print(chr(regs[7]))
	
	pc+=1
	
InstFuncs[0b00110111]=CarryBit
InstFuncs[0b00111111]=CarryBit
SetInstFuncs(0b00000100,0b00111100,0b00001000,Inr)
SetInstFuncs(0b00000101,0b00111101,0b00001000,Dcr)
InstFuncs[0b00101111]=Cma
InstFuncs[0b00100111]=Daa
SetInstFuncs(0b01000000,0b01111111,0b00000001,Mov)
InstFuncs[0b00000010]=Stax
InstFuncs[0b00010010]=Stax
InstFuncs[0b00001010]=Ldax
InstFuncs[0b00011010]=Ldax
SetInstFuncs(0b10000000,0b10111111,0b00000001,OpAcc)
SetInstFuncs(0b11000110,0b11111110,0b00001000,OpAcc)
InstFuncs[0b11000110]=Adi
SetInstFuncs(0b00000110,0b00111110,0b00001000,Mvi)
InstFuncs[0b00000111]=Rlc
InstFuncs[0b00001111]=Rrc
InstFuncs[0b00010111]=Ral
InstFuncs[0b00011111]=Rar
SetInstFuncs(0b11000101,0b11110101,0b00010000,Push)
SetInstFuncs(0b11000001,0b11110001,0b00010000,Pop)
SetInstFuncs(0b00001001,0b00111001,0b00010000,Dad)
SetInstFuncs(0b00000011,0b00110011,0b00010000,Inx)
SetInstFuncs(0b00001011,0b00111011,0b00010000,Dcx)
InstFuncs[0b11101011]=Xchg
InstFuncs[0b11100011]=Xthl
InstFuncs[0b11111001]=Sphl
SetInstFuncs(0b00000001,0b00110001,0b00010000,Lxi)
InstFuncs[0b00110010]=Sta
InstFuncs[0b00111010]=Lda
InstFuncs[0b00100010]=Shld
InstFuncs[0b00101010]=Lhld
InstFuncs[0b11101001]=Pchl
InstFuncs[0b11000010]=Jnz
InstFuncs[0b11000011]=Jmp
InstFuncs[0b11001010]=Jz
InstFuncs[0b11011010]=Jc
InstFuncs[0b11010010]=Jnc
InstFuncs[0b11110010]=Jp
InstFuncs[0b11111010]=Jm
InstFuncs[0b11101010]=Jpe
InstFuncs[0b11100010]=Jpo
InstFuncs[0b11000100]=Jnz
InstFuncs[0b11001101]=Jmp
InstFuncs[0b11001100]=Jz
InstFuncs[0b11011100]=Jc
InstFuncs[0b11010100]=Jnc
InstFuncs[0b11110100]=Jp
InstFuncs[0b11111100]=Jm
InstFuncs[0b11101100]=Jpe
InstFuncs[0b11100100]=Jpo
InstFuncs[0b11000000]=Rnz
InstFuncs[0b11001001]=Ret
InstFuncs[0b11001000]=Rz
InstFuncs[0b11011000]=Rc
InstFuncs[0b11010000]=Rnc
InstFuncs[0b11110000]=Rp
InstFuncs[0b11111000]=Rm
InstFuncs[0b11101000]=Rpe
InstFuncs[0b11100000]=Rpo
SetInstFuncs(0b11000111,0b11111111,0b00001000,Rst)
InstFuncs[0b11010011]=Out

def Show():
	#Update M so that it is displayed correctly
	regs[6]=mem[(regs[4]<<8)+regs[5]]
	
	print("B:"+hex(regs[0])+" C:"+hex(regs[1])+" D:"+hex(regs[2])+" E:"+hex(regs[3])+" H:"+hex(regs[4])+" L:"+hex(regs[5])+" M:"+hex(regs[6])+" A:"+hex(regs[7]))
	print("PSW:"+hex(regs[8]))
	print("SP:"+hex(sp))
	print("PC:"+hex(pc))
	print("@PC:"+hex(mem[pc]))
	print(InstFuncs[mem[pc]])
	showmem=0x478
	s=""
	for i in range(showmem,showmem+10):
		s+=hex(mem[i])+","
	print(s[:-1])
	
def SingleStep():
	global pc
	i = mem[pc]
	
	regs[6]=mem[(regs[4]<<8)+regs[5]]
	tmp=regs[6]
	
	InstFuncs[i](i)
	
	#if M has changed then the instruction must have acted on M, so update memory
	if regs[6]!=tmp:
		mem[(regs[4]<<8)+regs[5]]=regs[6]

inputBuffer=""

def CpmStub():
	global inputBuffer
	
	if pc==0:
		print("Restart")
		exit()
	if pc==5:
		if regs[1]==9:
			print(time.process_time())
			s=regs[3]+(regs[2]<<8)
			for i in range(1,80):
				c=chr(mem[s])
				if c=='$':
					break
				#print(mem[s])
				sys.stdout.write(c)
				s+=1
		elif regs[1]==2:
			print(regs[3])
			sys.stdout.write(chr(regs[3]))
		elif regs[1]==1:
			if len(inputBuffer)==0:
				inputBuffer=input()+str(chr(10))
				
			regs[7]=ord(inputBuffer[0])
			regs[5]=ord(inputBuffer[0])
			inputBuffer=inputBuffer[1:]
		else:
			print("Unrecognised CP/M call")
			print(regs[1])
		
#LoadFile()
mem[0]=0xc3
mem[1]=0x10
mem[2]=0x00
mem[3]=0x00
mem[4]=0x00
mem[5]=0xc9
mem[6]=0x00
mem[7]=0xd0

LoadHex()
#LoadAscFile("test.asc")

#print(time.process_time())
stepping=True
Show()
while True:
	if (pc==0x0010 or pc==0x00c1 or pc==0x001f) and 1==1:
		stepping=True
	if stepping:
		Show()
		c=input()
		if c=="g":
			stepping=False
	SingleStep()
	CpmStub()

