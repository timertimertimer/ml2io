function get_data(address, projectId=null, votingPower=null){
    const CryptoJS = require('crypto-js')
    const { Web3 } = require('web3')
    const web3 = new Web3()
    let r = {
        address: address,
        projectId: projectId || web3.utils.utf8ToHex(web3.utils.randomHex(32)),
        votingPower: votingPower || undefined
    }
    return [CryptoJS.AES.encrypt(JSON.stringify(r), "A1b2C3d4E5f6G7h8I9j0K!#").toString(), web3.utils.sha3(JSON.stringify(r)) || ""]
}