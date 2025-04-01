{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.nodejs-20_x
    pkgs.nodePackages.npm
  ];
}
