# L3 Artifact Policy

- fecha: `2026-03-24`
- estado: `PASS`

## Si va dentro del repo

- planes `.md`
- reports `.md`
- manifests `.txt` y `.json`
- scripts auxiliares pequenos en `artifacts_cva6/figure5_recovery/scripts`
- evidencia ligera necesaria para entender la recuperacion

## No deberia entrar en el camino normal del repo

- outputs de runs en `/tmp/sharc_cva6_figure5/*`
- logs grandes de Docker, Spike o Buildroot
- copias completas de payloads, kernels o rootfs salvo que sean evidencia puntual
- backups binarios usados solo para forense o rollback

## Carpetas candidatas a mantener fuera de un commit funcional minimo

- `artifacts_cva6/figure5_recovery/results/c8_backup_before_reinstall/`
- `artifacts_cva6/figure5_recovery/results/c9_forensic_triplet/`
- `artifacts_cva6/figure5_recovery/results/r0_reinstall_backup/`

## Decision operativa

- para dejar el repo funcional, basta con conservar documentacion, reports ligeros y scripts
- los binarios forenses y backups pesados se pueden archivar fuera o excluir del commit final

## Gate

- queda claro que entra como evidencia estable y que debe vivir fuera como artefacto efimero
