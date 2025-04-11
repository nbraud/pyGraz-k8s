{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; config.allowAliases = false; };
    inherit (pkgs) lib;
  in {
    packages.${system}.cloud-provider-kind = pkgs.buildGoModule rec {
      pname = "cloud-provider-kind";
      version = "0.6.0";

      src = pkgs.fetchFromGitHub {
        owner = "kubernetes-sigs";
        repo = "cloud-provider-kind";
        tag = "v${version}";
        hash = "sha256-6HdP6/uUCtLyZ7vjFGB2NLqe73v/yolRTUE5s/KyIIk=";
      };

      vendorHash = null;
    };

    devShells.${system}.default = pkgs.mkShellNoCC {
      buildInputs = with pkgs; [
        # kubernetes
        kubernetes-helm
        kind
        self.packages.${system}.cloud-provider-kind
        kubectl
        k9s

        # cilium (k8s networking)
        cilium-cli
        hubble

        # Pulumi (infra-as-code)
        (pulumi.withPackages (pu: [ pu.pulumi-python ]))
        (python3.withPackages (py: [ py.pip ]))
      ];

      PULUMI_CONFIG_PASSPHRASE = "pyGraz-k8s-test";
      LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc ];  # hack so the cygrpc wheel works
    };
  };
}
