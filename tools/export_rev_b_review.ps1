param(
    [string]$KiCadCli = 'kicad-cli',
    [string]$Out = 'build/rev-b-fab-review'
)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $board = 'hardware/rev-b/Gowuji-RevB.kicad_pcb'
    $schematic = 'hardware/rev-b/Gowuji-RevB.kicad_sch'
    New-Item -ItemType Directory -Force "$Out/gerber", "$Out/positions" | Out-Null
    function Invoke-KiCad {
        & $KiCadCli @args
        if ($LASTEXITCODE -ne 0) { throw "KiCad failed ($LASTEXITCODE): $args" }
    }
    Invoke-KiCad sch erc --exit-code-violations -o "$Out/erc.rpt" $schematic
    Invoke-KiCad pcb drc --schematic-parity --exit-code-violations -o "$Out/drc.rpt" $board
    Invoke-KiCad pcb export gerbers -l 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts' --subtract-soldermask -o "$Out/gerber/" $board
    Invoke-KiCad pcb export drill --format excellon --excellon-separate-th --excellon-oval-format route --generate-report --report-path "$Out/drill.txt" -o "$Out/gerber/" $board
    # Keep the hybrid Type-C socket in the review CPL; classify parts before assembly.
    Invoke-KiCad pcb export pos --side both --format csv --units mm --exclude-dnp -o "$Out/positions/review.csv" $board
    $positions = Import-Csv "$Out/positions/review.csv"
    $rows = foreach ($part in $positions) {
        $process = switch -Regex ($part.Ref) {
            '^J2$' { 'hybrid'; break }
            '^TP[1-5]$' { 'bare pad'; break }
            '^(J1|SW([1-9]|1[0-4]))$' { 'hand solder'; break }
            default { 'SMT' }
        }
        $part | Select-Object *, @{Name='Process'; Expression={$process}}
    }
    $rows | Export-Csv -NoTypeInformation -Encoding utf8 "$Out/positions/process.csv"
    $rows | Where-Object { $_.Process -eq 'SMT' } |
        Select-Object Ref, Val, Package, 'PosX', 'PosY', Rot, Side |
        Export-Csv -NoTypeInformation -Encoding utf8 "$Out/positions/smt-review.csv"
    Copy-Item hardware/rev-b/BOM.csv "$Out/BOM.csv"
    Copy-Item docs/rev-b-fab-notes.md "$Out/fabrication-notes.md"
    @'
ENGINEERING REVIEW ONLY — do not order from these exports.
Confirm stackup, controlled impedance and assembly parts/rotations first.
The placement CSV may contain hand-assembled and hybrid parts.
'@ | Set-Content -Encoding utf8 "$Out/README.txt"
}
finally {
    Pop-Location
}
