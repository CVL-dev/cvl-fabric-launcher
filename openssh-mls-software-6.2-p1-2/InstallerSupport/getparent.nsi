; GetParent
; input, top of stack  (e.g. C:\Program Files\Poop)
; output, top of stack (replaces, with e.g. C:\Program Files)
; modifies no other variables.
;
; Usage:
;   Push "C:\Program Files\Directory\Whatever"
;   Call GetParent
;   Pop $R0
;   ; at this point $R0 will equal "C:\Program Files\Directory"

Function GetParent
  Exch $R0 ; old $R0 is on top of stack
  Push $R1
  Push $R2
  StrCpy $R1 -1
  loop:
    StrCpy $R2 $R0 1 $R1
    StrCmp $R2 "" exit
    StrCmp $R2 "\" exit
    IntOp $R1 $R1 - 1
  Goto loop
  exit:
    StrCpy $R0 $R0 $R1
    Pop $R2
    Pop $R1
    Exch $R0 ; put $R0 on top of stack, restore $R0 to original value
FunctionEnd