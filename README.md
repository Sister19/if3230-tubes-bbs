### IF3230 - Parallel and Distributed Computing

# Tugas Besar 1 - Consensus Protocol Rust

## Deskripsi

Tugas besar ini merupakan implementasi dari algoritma [Raft](https://raft.github.io/raft.pdf) dalam bahasa pemrograman Rust. Implementasi ini dibuat untuk memenuhi tugas mata kuliah IF3230 - Sistem Paralel dan Terdistribusi.

## Cara Menjalankan

#### Server
```
python server.py <ip> <port> [<opt: contact ip> <opt: contact port>
```

#### Client
```
python client.py <client_ip> <client_port> <server_ip> <server_port>
```

Ketik `help` pada console client untuk bantuan
