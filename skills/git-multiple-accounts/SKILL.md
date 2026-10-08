---
name: git-multiple-accounts
description: "Use when GitHub identities differ across repositories."
version: 0.1.0
author: DeividArriaza, Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [git, github, ssh, identity, attribution]
---

# Git con cuentas personales y laborales

## Cuándo usar

Usar cuando el push, autor del commit o autor de PR corresponden a cuentas distintas, al configurar dos cuentas GitHub o al corregir documentación publicada con identidad equivocada. No cambiar credenciales globales para resolver un único repositorio.

## Requisitos y alcance

Git y OpenSSH; `gh` es opcional para PR/API. Leer AGENTS.md y revisar con `terminal` el directorio, rama, remoto, staging y worktree antes de actuar. En nodos remotos usar el bridge autorizado y comprobar salud/proyecto. Pedir autorización adicional antes de inspeccionar `.ssh` fuera del proyecto. Nunca leer/mostrar claves privadas, tokens o passphrases.

## Las tres identidades

1. **SSH:** identifica quién tiene permisos para fetch/push. Comprobar el saludo de `ssh -T` con la llave concreta.
2. **Git:** `user.name`/`user.email` generan author y committer del commit. GitHub asocia el correo a una cuenta, no a la llave que hizo push.
3. **GitHub API/PR:** `gh auth status` y `gh api user --jq .login` identifican quién crea un PR. Cambiar SSH no cambia la cuenta de `gh`.

Una rama no es un PR. Listar PRs en GitHub antes de crearlos, cerrarlos o afirmar que existen. El aviso Compare & pull request solo ofrece crearlo.

## Diagnóstico, mediante `terminal`

```text
git status --short
git branch --show-current
git remote get-url origin
git config --show-origin --get user.name
git config --show-origin --get user.email
git config --show-origin --get core.sshCommand
git log -1 --format=fuller
```

Sanitizar URLs si contienen credenciales. Consultar solo overrides SSH relevantes, no volcar toda la configuración. Verificar presencia de GIT_SSH/GIT_SSH_COMMAND sin imprimir secretos.

Con permiso, enumerar archivos públicos `.pub` mediante `search_files` o el bridge y obtener huellas con `ssh-keygen -lf <publica.pub>`. No inferir la cuenta por el comentario de una llave. Probar el candidato con el ejecutable SSH observado:

```text
ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -i <llave_existente> git@github.com
```

No aceptar hosts desconocidos automáticamente. GitHub puede devolver exit 1 aunque el saludo confirme autenticación exitosa. Conservar errores sanitizados: ausencia de saludo no prueba que la llave pertenezca a otra cuenta. En Windows verificar la ruta del cliente SSH, permisos y known_hosts si los resultados difieren.

## Configuración por repositorio

- Una llave de autenticación GitHub no puede registrarse simultáneamente en dos cuentas. Si hace falta, crear otra con autorización y nombre distinto; comprobar que no existe antes para no sobrescribirla.
- Acordar protección con passphrase o uso automatizado sin ella, explicar el compromiso y restringir permisos. Compartir únicamente la pública por un canal seguro; nunca versionar ninguna privada.
- El usuario agrega la pública a la cuenta correcta. Verificar saludo antes de configurar Git.
- Respaldar valores locales anteriores sin secretos y usar `git config --local user.name <nombre>` y `git config --local user.email <correo_verificado_o_noreply>`; no modificar identidad laboral global.
- Para noreply, obtener el valor de GitHub Settings/Emails o verificar ID/login de cuenta con API antes de derivar el formato. Confirmar después la atribución mediante API del commit publicado.
- Configurar `core.sshCommand` local con cliente y ruta privada verificadas, `IdentitiesOnly=yes` y quoting adecuado. Usar placeholders en documentación; no publicar rutas privadas ni material de claves.
- Releer origen/valores efectivos. Verificar author y committer antes de cada publicación. Las variables GIT_AUTHOR_* y GIT_COMMITTER_* pueden sobrescribir la configuración; no asumir que cambiar user.email basta.
- No cambiar ni cerrar sesión laboral de `gh` silenciosamente. Solo crear/gestionar PRs tras comprobar la cuenta correcta; si no está disponible, solicitar autenticación por UI sin recoger secretos en chat.

## Publicación y reparación

1. Fetch y comparar rama/upstream sin borrar cambios locales. Con divergencia, detenerse antes de integrar. No usar reset --hard.
2. Stagear exclusivamente archivos autorizados; revisar contenido, `git diff --cached --name-only` y `git diff --cached --check`. No `git add .` indiscriminado.
3. Crear commit sin trailers Co-authored-by no solicitados. Verificar author/committer y archivos.
4. Push normal por SSH. Comparar `git rev-parse HEAD` con `git ls-remote origin refs/heads/<rama>` y confirmar autor/committer en API de GitHub.
5. Si un commit ya publicado tiene autor incorrecto, no se arregla con un segundo commit: el original mantiene su autor. Preferir rama nueva desde la base correcta y reconstruir solo los cambios propios con identidad verificada; conservar rama original hasta autorización para retirarla.
6. Amend/rebase y force-push requieren permiso explícito para reescribir historia compartida. Si se autoriza, usar force-with-lease con hash remoto esperado, nunca force ciego.
7. No mergear, cerrar, sustituir ni borrar PRs/ramas sin alcance autorizado. Si se pide corregir PR, verificar primero existencia, autor, base/head, checks y cambios ajenos. El autor de un PR existente no se cambia editando commits.

## Errores frecuentes

- Clonar no demuestra permisos de push: un repo público puede ser legible para otra identidad.
- `Key already in use` indica registro previo en otra cuenta o deploy key; no prueba que la llave esté en la cuenta deseada.
- SSH personal con correo Git laboral produce commits atribuidos a la cuenta laboral.
- `gh` laboral puede crear PRs laborales aunque Git use SSH personal.
- `git diff --check` no valida archivos sin seguimiento; stagear los archivos exactos o verificar contenido/encoding explícitamente.
- No confundir timeout de bridge con tarea fallida: consultar estado y transcript antes de reintentar.

## Verificación final

Reportar cuenta SSH, author/committer asociados por GitHub, hash, rama/upstream, URL remota, estado worktree y ahead/behind. Leer de vuelta archivos publicados y comprobar links/frontmatter para una skill. Diferenciar rama publicada, PR abierto y merge completado. Declarar ramas antiguas conservadas y bloqueos de API/autenticación.
