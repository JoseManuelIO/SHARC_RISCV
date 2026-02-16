ENTRY(_start)

MEMORY
{
  ROM (rx) : ORIGIN = 0x1c000000, LENGTH = 0x00190000
  RAM (rwx) : ORIGIN = 0x1c010000, LENGTH = 0x00180000
}

SECTIONS
{
  .init : {
    *(.init*)
  } > ROM

  .text : {
    *(.text*)
    *(.rodata*)
  } > ROM

  /* Shared data section at fixed address for host communication */
  .shared_data 0x1c010000 : {
    PROVIDE(_shared_data_start = .);
    *(.shared_data*)
    PROVIDE(_shared_data_end = .);
  } > RAM

  .data : {
    PROVIDE(_data_start = .);
    *(.data*)
    PROVIDE(_data_end = .);
  } > RAM AT > ROM
  
  PROVIDE(_data_load_start = LOADADDR(.data));

  .bss : {
    PROVIDE(_bss_start = .);
    *(.bss*)
    *(COMMON)
    PROVIDE(_bss_end = .);
  } > RAM

  PROVIDE(_end = .);
  PROVIDE(stack = ORIGIN(RAM) + LENGTH(RAM));
  PROVIDE(_stack_top = ORIGIN(RAM) + LENGTH(RAM));

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.gnu_debuglink)
    *(.gnu.lto_*)
  }
}
