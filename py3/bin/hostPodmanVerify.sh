#!/bin/bash
# hostPodmanVerify.sh --- Check that THIS host can run rootless-sysd containers.
#
# HOST-scoped readiness check (not tied to any image or Debian release):
# rootless Podman + crun + cgroup v2 with controller delegation + a working
# user systemd/D-Bus session + a store (graphroot) on a local disk with free
# space. Inspects the host only; builds/runs nothing.
#
# Lives in the bisos.dockerProc package bin/ alongside dockerProc-sbom.cs
# (also host-provisioning scoped). Image-specific concerns (base image
# presence, etc.) belong in each image dir's build.bash / verify.sh, not here.
#
# Usage:   ./hostPodmanVerify.sh
# Exit:    0 = GO (all hard requirements met), non-zero = NO-GO.

set -u

PASS=0
FAIL=0
WARN=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
yellow(){ printf '\033[33m%s\033[0m' "$1"; }

ok()   { printf '  [%s] %s\n' "$(green PASS)" "$1"; PASS=$((PASS+1)); }
bad()  { printf '  [%s] %s\n' "$(red FAIL)" "$1";  FAIL=$((FAIL+1)); }
warn() { printf '  [%s] %s\n' "$(yellow WARN)" "$1"; WARN=$((WARN+1)); }

echo "== Host readiness for rootless-sysd containers =="

# 1. Not running as root --- the whole point is rootless.
if [ "$(id -u)" -eq 0 ]; then
  warn "running as root (uid 0); rootless-sysd is meant to run as a normal user"
else
  ok "running as non-root user ($(id -un), uid $(id -u))"
fi

# 2. Podman installed.
if command -v podman >/dev/null 2>&1; then
  ok "podman installed ($(podman --version 2>/dev/null))"
  HAVE_PODMAN=1
else
  bad "podman NOT installed --- install: podman crun uidmap fuse-overlayfs dbus-user-session slirp4netns passt"
  HAVE_PODMAN=0
fi

# 3. cgroup v2 (unified hierarchy).
CG=$(stat -fc %T /sys/fs/cgroup 2>/dev/null)
if [ "$CG" = "cgroup2fs" ]; then
  ok "cgroup v2 (cgroup2fs) --- rootless delegation is possible"
else
  bad "cgroup is '$CG' (need cgroup2fs). This host is on cgroup v1/hybrid; rootless-sysd cannot work here."
fi

# 4. OCI runtime is crun (best rootless cgroup v2 delegation).
if [ "$HAVE_PODMAN" -eq 1 ]; then
  OCI=$(podman info --format '{{.Host.OCIRuntime.Name}}' 2>/dev/null)
  if [ "$OCI" = "crun" ]; then
    ok "OCI runtime is crun"
  else
    warn "OCI runtime is '${OCI:-unknown}' (crun recommended for rootless systemd)"
  fi
fi

# 5. subuid / subgid ranges for this user (mandatory for rootless userns).
if grep -q "^$(id -un):" /etc/subuid 2>/dev/null && grep -q "^$(id -un):" /etc/subgid 2>/dev/null; then
  ok "subuid/subgid ranges present for $(id -un)"
else
  bad "no subuid/subgid range for $(id -un) --- run: sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(id -un)"
fi

# 6. Working user session (XDG_RUNTIME_DIR + user systemd/D-Bus).
#    crun's default cgroup manager is 'systemd': to create a container it asks
#    THIS user's systemd over sd-bus to make a transient scope. With no user
#    session (e.g. you `su`'d in, or a non-login SSH shell) that call fails:
#      sd-bus call ... org.freedesktop.systemd1 ... Input/output error
#    A passing cgroup check does NOT imply a reachable session bus --- this is
#    the check that catches that.
CGMGR=""
if [ "$HAVE_PODMAN" -eq 1 ]; then
  CGMGR=$(podman info --format '{{.Host.CgroupManager}}' 2>/dev/null)
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "${XDG_RUNTIME_DIR:-/nonexistent}" ]; then
  ok "XDG_RUNTIME_DIR set ($XDG_RUNTIME_DIR)"
elif [ "$CGMGR" = "systemd" ]; then
  bad "XDG_RUNTIME_DIR unset/missing --- no user session. With the systemd cgroup manager, podman build/run fail (sd-bus I/O error). Log in as this user directly (not su)."
else
  warn "XDG_RUNTIME_DIR unset/missing (cgroup manager '${CGMGR:-?}' may tolerate it)"
fi

if systemctl --user show-environment >/dev/null 2>&1; then
  ok "user systemd/D-Bus session reachable (systemctl --user works)"
elif [ "$CGMGR" = "systemd" ]; then
  bad "no user systemd/D-Bus session --- systemd cgroup manager will fail. Fix: log in directly (not su) + 'loginctl enable-linger $(id -un)'; or build with 'podman --cgroup-manager=cgroupfs ...'"
else
  warn "no user systemd/D-Bus session (cgroup manager '${CGMGR:-?}')"
fi

# linger: needed for the Quadlet per-engineer model to run without a login.
LINGER=$(loginctl show-user "$(id -un)" 2>/dev/null | sed -n 's/^Linger=//p')
if [ "$LINGER" = "yes" ]; then
  ok "linger enabled (user services persist without an active login)"
else
  warn "linger not enabled --- needed for the Quadlet per-engineer model (loginctl enable-linger $(id -un))"
fi

# 7. cgroup v2 controller delegation for the user session.
DELEG_FILE="/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers"
if [ -r "$DELEG_FILE" ]; then
  CONTROLLERS=$(cat "$DELEG_FILE" 2>/dev/null)
  MISSING=""
  for c in cpu io memory pids; do
    case " $CONTROLLERS " in *" $c "*) : ;; *) MISSING="$MISSING $c" ;; esac
  done
  if [ -z "$MISSING" ]; then
    ok "controller delegation OK (cpu io memory pids)"
  else
    warn "delegated controllers = '$CONTROLLERS'; missing:$MISSING --- add a Delegate= drop-in on user@.service"
  fi
else
  warn "cannot read $DELEG_FILE (no delegated user cgroup?) --- systemd resource control inside may be limited"
fi

# 8. Podman store (graphroot): must be on a local disk with room to spare.
#    overlay does not work reliably on NFS, and a near-full store filesystem
#    makes builds fail mid-layer with "no space left on device".
if [ "$HAVE_PODMAN" -eq 1 ]; then
  GRAPHROOT=$(podman info --format '{{.Store.GraphRoot}}' 2>/dev/null)
  if [ -n "$GRAPHROOT" ]; then
    FSTYPE=$(stat -f -c %T "$GRAPHROOT" 2>/dev/null)
    USEPCT=$(df -P "$GRAPHROOT" 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
    AVAILK=$(df -Pk "$GRAPHROOT" 2>/dev/null | awk 'NR==2{print $4}')
    AVAILG=$(( ${AVAILK:-0} / 1024 / 1024 ))

    case "$FSTYPE" in
      nfs|nfs4)
        bad "graphroot on NFS ($GRAPHROOT, fstype=$FSTYPE) --- overlay driver is unreliable on NFS; move it to a local disk (storage.conf graphroot=)" ;;
      "")
        warn "could not determine graphroot fstype ($GRAPHROOT)" ;;
      *)
        ok "graphroot on local fs ($FSTYPE): $GRAPHROOT" ;;
    esac

    if [ -n "$USEPCT" ]; then
      if [ "$USEPCT" -ge 95 ] || [ "${AVAILG:-0}" -lt 3 ]; then
        bad "graphroot filesystem ${USEPCT}% full (~${AVAILG}G free) --- image builds will fail with 'no space left on device'"
      elif [ "$USEPCT" -ge 90 ]; then
        warn "graphroot filesystem ${USEPCT}% full (~${AVAILG}G free) --- low headroom for image builds"
      else
        ok "graphroot free space OK (${USEPCT}% used, ~${AVAILG}G free)"
      fi
    else
      warn "could not determine graphroot free space for $GRAPHROOT"
    fi
  else
    warn "could not determine graphroot (podman info)"
  fi
fi

echo "== $PASS passed, $WARN warnings, $FAIL failed =="
if [ "$FAIL" -eq 0 ]; then
  echo "GO: hard requirements met (review any WARNs above)."
else
  echo "NO-GO: $FAIL blocking requirement(s) unmet. rootless-sysd will not run here as-is."
fi
[ "$FAIL" -eq 0 ]
