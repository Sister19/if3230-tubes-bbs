### IF3230 - Parallel and Distributed Computing

# Tugas Besar 1 - Consensus Protocol Rust

## Deskripsi

Tugas besar ini merupakan implementasi dari algoritma [Raft](https://raft.github.io/raft.pdf) dalam bahasa pemrograman Rust. Implementasi ini dibuat untuk memenuhi tugas mata kuliah IF3230 - Sistem Paralel dan Terdistribusi.

## [ON PROGRESS] Library

(blom gaes nanti cherrypick utk dipake maybe) openraft, axum/tonic/actix, tokio/async_std, reqwest, serde & turunannya, async_trait, bytes, env_logger, log, ctrlc.

## [ON PROGRESS] Cara menjalankan program

1. Buka terminal,
2. Jalankan perintah `make server` untuk mem-*build* executable server,
3. Jalankan perintah `cargo run server -p <nomor-port>` untuk menjalankan satu server dengan konfigurasi lorem ipsum. Jalankan perintah tersebut dengan konfigurasi lain untuk menjalankan server yang lain.
4. Jalankan perintah `make client` untuk mem-*build* executable client,
5. Jalankan perintah `cargo run client -p <nomor-port>` untuk menjalankan satu server dengan konfigurasi lorem ipsum.

