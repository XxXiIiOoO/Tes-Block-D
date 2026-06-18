/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337,
      mining: {
        auto: true,
        interval: 0,
      },
    },
  },
  solidity: "0.8.24",
};
