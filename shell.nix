{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {

  packages = [
    pkgs.python3
    (pkgs.python3.withPackages (ps: [
      ps.pip
      ps.flask
      ps.flask-socketio
    ]))
    pkgs.stdenv.cc.cc.lib
    pkgs.libz
    pkgs.libevent
    pkgs.openssl
  ];

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
    pkgs.libz
    pkgs.libevent
    pkgs.openssl
  ];

}
