//! Disposable lexical index: never stores evidence, reinforcement or memory state.
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};

type Record = (String, i64, HashMap<String, u64>);
struct Document {
    id: String,
    seq: i64,
    length: u64,
    terms: Vec<String>,
}

#[pyclass]
struct BM25Kernel {
    k1: f64,
    b: f64,
    documents: Vec<Option<Document>>,
    free: Vec<usize>,
    ids: HashMap<String, usize>,
    postings: HashMap<String, HashMap<usize, u64>>,
    total_length: u64,
}

impl BM25Kernel {
    fn remove_id(&mut self, id: &str) {
        if let Some(slot) = self.ids.remove(id) {
            let doc = self.documents[slot].take().expect("indexed document exists");
            self.total_length -= doc.length;
            for term in doc.terms {
                let posting = self.postings.get_mut(&term).expect("indexed term exists");
                posting.remove(&slot);
                if posting.is_empty() {
                    self.postings.remove(&term);
                }
            }
            self.free.push(slot);
        }
    }

    fn rank(&self, terms: Vec<String>, top_k: usize, excluded: HashSet<String>) -> Vec<(String, f64)> {
        if top_k == 0 || self.ids.is_empty() { return Vec::new(); }
        let n = self.ids.len() as f64;
        let average = (self.total_length as f64 / n).max(1e-12);
        let excluded_slots: HashSet<usize> = excluded.iter().filter_map(|id| self.ids.get(id).copied()).collect();
        let mut terms = terms;
        terms.sort();
        terms.dedup();
        let mut scores: HashMap<usize, f64> = HashMap::new();
        for term in terms {
            if let Some(posting) = self.postings.get(&term) {
                let df = posting.len() as f64;
                let idf = ((n - df + 0.5) / (df + 0.5)).ln_1p();
                for (&slot, &tf) in posting {
                    if excluded_slots.contains(&slot) { continue; }
                    let doc = self.documents[slot].as_ref().expect("posting document exists");
                    let norm = self.k1 * (1.0 - self.b + self.b * doc.length as f64 / average);
                    *scores.entry(slot).or_insert(0.0) += idf * tf as f64 * (self.k1 + 1.0) / (tf as f64 + norm);
                }
            }
        }
        let mut rows: Vec<(usize, f64)> = scores.into_iter().collect();
        let compare = |a: &(usize, f64), b: &(usize, f64)| -> Ordering {
            let da = self.documents[a.0].as_ref().unwrap();
            let db = self.documents[b.0].as_ref().unwrap();
            b.1.total_cmp(&a.1).then_with(|| da.seq.cmp(&db.seq)).then_with(|| da.id.cmp(&db.id))
        };
        if top_k < rows.len() {
            rows.select_nth_unstable_by(top_k, compare);
            rows.truncate(top_k);
        }
        rows.sort_unstable_by(compare);
        rows.into_iter().map(|(slot, score)| (self.documents[slot].as_ref().unwrap().id.clone(), score)).collect()
    }
}

#[pymethods]
impl BM25Kernel {
    #[new]
    fn new(k1: f64, b: f64) -> PyResult<Self> {
        if !k1.is_finite() || k1 <= 0.0 || !b.is_finite() || !(0.0..=1.0).contains(&b) {
            return Err(PyValueError::new_err("BM25 requires finite k1 > 0 and 0 <= b <= 1"));
        }
        Ok(Self { k1, b, documents: Vec::new(), free: Vec::new(), ids: HashMap::new(),
            postings: HashMap::new(), total_length: 0 })
    }

    fn upsert_batch(&mut self, records: Vec<Record>) -> PyResult<()> {
        // Validate every record before mutation, including duplicate IDs in a batch.
        let mut projected_total = self.total_length as u128;
        let mut projected_lengths: HashMap<&str, u64> = HashMap::new();
        for (id, _, counts) in &records {
            if counts.values().any(|&tf| tf == 0) || counts.values().try_fold(0u64, |sum, &tf| sum.checked_add(tf)).is_none() {
                return Err(PyValueError::new_err("term counts must be positive and length must fit u64"));
            }
            let length: u64 = counts.values().sum();
            let old_length = projected_lengths.get(id.as_str()).copied().unwrap_or_else(||
                self.ids.get(id).map(|&slot| self.documents[slot].as_ref().unwrap().length).unwrap_or(0));
            projected_total = projected_total - old_length as u128 + length as u128;
            if projected_total > u64::MAX as u128 {
                return Err(PyValueError::new_err("corpus total length must fit u64"));
            }
            projected_lengths.insert(id.as_str(), length);
        }
        for (id, seq, counts) in records {
            self.remove_id(&id);
            let slot = self.free.pop().unwrap_or_else(|| { self.documents.push(None); self.documents.len() - 1 });
            let length: u64 = counts.values().sum();
            let terms = counts.keys().cloned().collect();
            for (term, tf) in counts { self.postings.entry(term).or_default().insert(slot, tf); }
            self.total_length += length;
            self.ids.insert(id.clone(), slot);
            self.documents[slot] = Some(Document { id, seq, length, terms });
        }
        Ok(())
    }

    fn remove_batch(&mut self, ids: Vec<String>) {
        for id in ids { self.remove_id(&id); }
    }

    fn search(&self, py: Python<'_>, terms: Vec<String>, top_k: usize, excluded: HashSet<String>) -> Vec<(String, f64)> {
        // Only owned Rust data cross the detached section; PyO3 guards self's borrow.
        py.detach(|| self.rank(terms, top_k, excluded))
    }

    // Benchmark-only observation: conversion occurs outside the Rust timer.
    // Ordinary production search remains uninstrumented.
    fn search_timed(&self, py: Python<'_>, terms: Vec<String>, top_k: usize, excluded: HashSet<String>) -> (Vec<(String, f64)>, u128) {
        py.detach(|| {
            let start = std::time::Instant::now();
            let rows = self.rank(terms, top_k, excluded);
            let nanoseconds = start.elapsed().as_nanos();
            (rows, nanoseconds)
        })
    }

    #[getter]
    fn n(&self) -> usize { self.ids.len() }
}

#[pymodule(gil_used = true)]
fn _mnemosis_rust(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<BM25Kernel>()?;
    module.add("API_VERSION", 1)?;
    module.add("BUILD_PROFILE", if cfg!(debug_assertions) { "debug" } else { "release" })?;
    Ok(())
}
