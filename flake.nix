{
  description = "The usdAECO suite: release pins, schema domains, tools and documentation";

  inputs = {
    # BEGIN GENERATED INPUTS
    usdaeco-core.url = "github:criad-com/usdaeco-core?ref=v0.9.5";
    usdaeco-core.flake = false;
    usdaeco-axis.url = "github:criad-com/usdaeco-axis?ref=v0.1.5";
    usdaeco-axis.flake = false;
    usdaeco-buildup.url = "github:criad-com/usdaeco-buildup?ref=v0.2.5";
    usdaeco-buildup.flake = false;
    usdaeco-wall.url = "github:criad-com/usdaeco-wall?ref=v0.2.5";
    usdaeco-wall.flake = false;
    usdaeco-pipe.url = "github:criad-com/usdaeco-pipe?ref=v0.2.5";
    usdaeco-pipe.flake = false;
    usdaeco-cctv.url = "github:criad-com/usdaeco-cctv?ref=v0.5.6";
    usdaeco-cctv.flake = false;
    usdaeco-clash.url = "github:criad-com/usdaeco-clash?ref=v0.2.3";
    usdaeco-clash.flake = false;
    usdaeco-plan.url = "github:criad-com/usdaeco-plan?ref=v0.1.4";
    usdaeco-plan.flake = false;
    usdaeco-repeat.url = "github:criad-com/usdaeco-repeat?ref=v0.2.1";
    usdaeco-repeat.flake = false;
    usdaeco-compliance.url = "github:criad-com/usdaeco-compliance?ref=v0.1.3";
    usdaeco-compliance.flake = false;
    usdaeco-solid.url = "github:criad-com/usdaeco-solid?ref=v0.1.5";
    usdaeco-solid.flake = false;
    usdaeco-sync.url = "github:criad-com/usdaeco-sync?ref=v0.5.5";
    usdaeco-sync.flake = false;
    usdaeco-ifc.url = "github:criad-com/usdaeco-ifc?ref=v0.2.3";
    usdaeco-ifc.flake = false;
    usdaeco-revit.url = "github:criad-com/usdaeco-revit?ref=v0.1.5";
    usdaeco-revit.flake = false;
    usdaeco-bonsai.url = "github:criad-com/usdaeco-bonsai?ref=v0.1.6";
    usdaeco-bonsai.flake = false;
    usdaeco-toolchain.url = "github:criad-com/usdaeco-toolchain?ref=v0.3.10";
    aeco-toolchain.url = "github:criad-com/aeco-toolchain?ref=v0.4.0";
    usdaeco-cctv-exec.url = "github:criad-com/usdaeco-cctv-exec?ref=v0.2.4";
    usdaeco-cctv-exec.flake = false;
    usdSolid.url = "github:criad-com/usdSolid?ref=v0.1.6";
    usdSolid.flake = false;
    usdSolidOcct.url = "github:criad-com/usdSolidOcct?ref=v0.1.5";
    usdSolidOcct.flake = false;
    usdaeco-datacentre.url = "github:criad-com/usdaeco-datacentre?ref=v0.4.9";
    usdaeco-datacentre.flake = false;
    usdaeco-scenarios.url = "github:criad-com/usdaeco-scenarios?ref=v0.8.1";
    usdaeco-scenarios.flake = false;
    usdaeco-board.url = "github:criad-com/usdaeco-board?ref=v0.1.5";
    usdaeco-board.flake = false;
    usdaeco-toolchain.inputs.aeco-toolchain.follows = "aeco-toolchain";
    usdaeco-toolchain.inputs.core.follows = "usdaeco-core";
    nixpkgs.follows = "aeco-toolchain/nixpkgs";
    # END GENERATED INPUTS
  };

  outputs = inputs@{ self, nixpkgs, usdaeco-toolchain, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      suite = builtins.fromJSON (builtins.readFile ./suite.json);
      declared = builtins.removeAttrs (import ./flake.nix).inputs [ "nixpkgs" ];
      expected = builtins.listToAttrs (map (repo: {
        name = repo.name;
        value = "github:criad-com/${repo.name}?ref=${repo.tag}";
      }) suite.repos);
      actual = builtins.mapAttrs (_: input: input.url) declared;
      pinsAgree = expected == actual
        && builtins.length suite.repos == builtins.length (builtins.attrNames expected)
        && builtins.all (name:
          (declared.${name}.flake or true)
          == builtins.elem name [ "usdaeco-toolchain" "aeco-toolchain" ])
          (builtins.attrNames declared);
    in {
      # The assertion is pure evaluation; --no-build requires no package builds.
      lib.pins = assert pinsAgree; true;
      checks = eachSystem (system: {
        pins = assert pinsAgree;
          nixpkgs.legacyPackages.${system}.runCommand "usdaeco-suite-pins" { } ''
            touch "$out"
          '';
      });
      devShells = eachSystem (system: {
        default = nixpkgs.legacyPackages.${system}.mkShell {
          packages = [ usdaeco-toolchain.packages.${system}.pythonEnv ];
          shellHook = ''
            unset PYTHONPATH
            export PYTHON=python3
          '';
        };
      });
    };
}
