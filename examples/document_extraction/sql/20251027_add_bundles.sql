-- Supabase DDL for document bundles support.
-- Run these statements against the openai schema in your Supabase Postgres database.

create extension if not exists pgcrypto;

create table if not exists openai.bundles (
    id uuid primary key default gen_random_uuid(),
    org_id int not null,
    primary_document_id uuid not null references openai.documents(id) on delete restrict,
    key_po_number text,
    key_invoice_number text,
    key_summary jsonb,
    documents_snapshot jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists bundles_org_idx on openai.bundles(org_id);

create unique index if not exists bundles_unique_po
    on openai.bundles(org_id, key_po_number)
    where key_po_number is not null;

create unique index if not exists bundles_unique_invoice
    on openai.bundles(org_id, key_invoice_number)
    where key_invoice_number is not null;

create table if not exists openai.bundle_documents (
    bundle_id uuid not null references openai.bundles(id) on delete cascade,
    document_id uuid not null references openai.documents(id) on delete cascade,
    doc_type text not null,
    added_at timestamptz not null default now(),
    document_snapshot jsonb,
    primary key (bundle_id, document_id)
);

create index if not exists bundle_documents_bundle_idx on openai.bundle_documents(bundle_id);

create index if not exists bundle_documents_doc_idx on openai.bundle_documents(document_id);

create unique index if not exists unique_bundle_for_po_invoice
    on openai.bundle_documents(document_id)
    where doc_type in ('invoice', 'purchase_order');

alter table openai.documents
    add column if not exists assigned_bundles jsonb not null default '[]'::jsonb;

alter table openai.documents
    add column if not exists document_data jsonb;

