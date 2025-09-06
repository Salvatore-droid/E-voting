import json
import hashlib
from time import time
from uuid import uuid4
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from web3 import Web3, HTTPProvider
import os
from django.conf import settings

class Blockchain:
    def __init__(self):
        # Connect to Ethereum node (you can use Infura or run your own node)
        self.w3 = Web3(HTTPProvider(settings.BLOCKCHAIN_NODE_URL))
        
        # Load contract ABI and address
        with open(settings.BLOCKCHAIN_CONTRACT_ABI_PATH, 'r') as abi_file:
            self.contract_abi = json.load(abi_file)
        
        self.contract_address = settings.BLOCKCHAIN_CONTRACT_ADDRESS
        self.contract = self.w3.eth.contract(
            address=self.contract_address, 
            abi=self.contract_abi
        )
        
        # Admin account for transactions
        self.admin_account = settings.BLOCKCHAIN_ADMIN_ACCOUNT
        self.private_key = settings.BLOCKCHAIN_PRIVATE_KEY

    def cast_vote(self, voter_id, candidate_id, position_id, election_id):
        # Create a unique vote hash
        vote_data = f"{voter_id}-{candidate_id}-{position_id}-{election_id}-{time()}"
        vote_hash = hashlib.sha256(vote_data.encode()).hexdigest()
        
        # Prepare transaction
        nonce = self.w3.eth.getTransactionCount(self.admin_account)
        
        # Build transaction
        transaction = self.contract.functions.castVote(
            vote_hash, 
            voter_id, 
            candidate_id, 
            position_id, 
            election_id
        ).buildTransaction({
            'chainId': settings.BLOCKCHAIN_CHAIN_ID,
            'gas': 2000000,
            'gasPrice': self.w3.toWei('50', 'gwei'),
            'nonce': nonce,
        })
        
        # Sign transaction
        signed_txn = self.w3.eth.account.signTransaction(transaction, private_key=self.private_key)
        
        # Send transaction
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        
        return receipt, vote_hash

    def verify_vote(self, vote_hash):
        return self.contract.functions.verifyVote(vote_hash).call()

    def get_election_results(self, election_id):
        return self.contract.functions.getElectionResults(election_id).call()

    def generate_keys(self):
        # Generate RSA key pair for voter verification
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()

# Singleton instance
blockchain = Blockchain()