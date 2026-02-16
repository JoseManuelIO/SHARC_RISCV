.section .init
.global _start

_start:
    # Set up stack pointer
    la sp, _stack_top
    
    # Clear BSS section
    la t0, _bss_start
    la t1, _bss_end
bss_clear_loop:
    bge t0, t1, bss_clear_done
    sw zero, 0(t0)
    addi t0, t0, 4
    j bss_clear_loop
bss_clear_done:
    
    # Call main
    call main
    
    # Halt execution with WFI (Wait For Interrupt)
1:
    wfi
    j 1b
