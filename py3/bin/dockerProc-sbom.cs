#!/usr/bin/env python

from bisos.sbom import pkgsSeed  # pkgsSeed.plantWithWhich("seedSbom.cs")
ap = pkgsSeed.aptPkg

aptPkgsList = [
    # Vagrant-VM model (fresh-Debian test rig via QEMU/libvirt).
    ap("vagrant"),
    ap("packer"),

    # Rootless-sysd model: rootless Podman host running systemd-PID-1
    # containers (debian/{12,13}/rootless-sysd) without --privileged.
    ap("podman"),            # container engine
    ap("crun"),              # OCI runtime; clean cgroups-v2 delegation for rootless systemd
    ap("uidmap"),            # newuidmap/newgidmap — mandatory for rootless userns
    ap("fuse-overlayfs"),    # rootless overlay storage driver
    ap("dbus-user-session"), # systemctl --user / loginctl enable-linger (Quadlet per-engineer model)
    ap("slirp4netns"),       # rootless networking / port forwarding
    ap("passt"),             # provides pasta — preferred rootless net on deb13

    # Multi-arch image builds (build.bash without -d, linux/amd64,arm64).
    ap("qemu-user-static"),  # cross-arch emulation
    ap("binfmt-support"),    # binfmt registration for qemu-user-static
]

pkgsSeed.setup(
    aptPkgsList=aptPkgsList,
)
