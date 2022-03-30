import hashlib 
import json
from operator import length_hint
from time import time
from urllib import response
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request
import requests
from flask_cors import CORS



class Blockchain(object):
    def __init__(self): 
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.amount = 0

        # genesis block
        self.new_block(previous_hash=1, proof=100)
    
    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        # Creates a new block and adds to chain
        
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # Reset

        self.current_transactions = []
        self.chain.append(block)
        print(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        # Adds a new transaction to the list of transactions
        
        self.current_transactions.append({
            'sender':sender,
            'recipient': recipient,
            'amount': amount
        })

        self.amount += amount

        # reward system
        if self.last_block['index'] % 4413 == 0:
            self.current_transactions.append({
                'sender': '0',
                'recipient': sender,
                'amount': 100
            })

            self.amount += 100

        # limit
        if self.amount > 21*10**6:
            self.current_transactions = []
            # handle the case where the amount is greater than 21 million
            # reset the current transactions
            # something where /mine will not work.

        return self.last_block['index'] + 1
        # increments the last block of the chain 

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """
        # Hashes a block
        # Creates a SHA-256 hash of a block
        
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest() 
    
    @property
    def last_block(self):
        """
        Returns the last Block in the chain
        :return: <dict> last Block
        """
        # returns the last block of the chain.  
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0

        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://
        :return: None
        """
        # adding a new list of nodes
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        # determining if the blockchain is valid
        

        last_block = chain[0]
        current_index = 1 

        # Loop through each block and verifing both hash and proof
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n-----------\n')

            if block['previous_hash'] != self.hash(last_block):
                return False 
            
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False 
            
            last_block = block 
            current_index += 1
        return True 

    def resolve_conflicts(self):
        
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        # replaces chain with the longest one on our network 
        # therefore resolving conflicts that may turn up

        # Visites all neighbouring nodes and using valid chain will verify
        # whether the chain is valid and if the length of the chain is greater
        # then it will replace the chain. 

        neighbors = self.nodes 
        new_chain = None 

        max_length = len(self.chain)
        # verify each chain from each node
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200: 
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain 
        if new_chain:
            self.chain = new_chain 
            return True 
        
        return False 

app = Flask(__name__)
CORS(app)

node_id = str(uuid4()).replace('-', '')
chain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = chain.last_block
    last_proof = last_block['proof']
    proof = chain.proof_of_work(last_proof)

    chain.new_transaction(
        sender="0",
        recipient=node_id,
        amount=1
    )
    previous_hash = chain.hash(last_block)
    block = chain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    # if we are missing any values from requirement
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    index = chain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to the Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': chain.chain,
        'length': len(chain.chain)
    }
    return jsonify(response), 200 

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """
    Registers a new node on the network
    Make sure to add both the address and the port number http://{}:{}
    to both nodes
    """
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
    
    for node in nodes:
        chain.register_node(node)

    response = {
        'message': "New nodes have been added",
        "total_nodes": list(chain.nodes)
    }

    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """
    Resolve conflicts by replacing the chain with the longest one
    :return: <bool> True if chain is replaced, False if not
    """
    replaced = chain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': chain.chain
        }
    else:
        response = {
            'message':'Our chain is authoritative',
            'chain': chain.chain
        }
    
    return jsonify(response), 200


@app.route('/nodes/get', methods=['GET'])
def get_nodes():
    nodes = list(chain.nodes)
    response = {
        'nodes': nodes
    }
    return jsonify(response), 200

@app.route('/nodes/reset', methods=['GET'])
def reset_nodes():
    chain.nodes = set()
    response = {
        'message': 'Nodes have been reset'
    }
    return jsonify(response), 200

@app.route('/amount', methods=['GET'])
def amount():
    response = {
        'amount': chain.amount
    }
    return jsonify(response), 200

# split between flask and blockchain scripts

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(port=port)

