-- ============================================================
-- Personal Budget Tracker — core schema (PostgreSQL 14+)
-- ============================================================

create extension if not exists pgcrypto;

-- ---------- Enums ----------
create type category_type as enum ('income', 'fixed_expense', 'variable_expense');
create type txn_direction as enum ('debit', 'credit');
create type statement_format as enum ('csv', 'xlsx', 'pdf');
create type statement_status as enum ('processing', 'parsed', 'failed');
create type rule_source as enum ('seed', 'ai_suggestion', 'user_correction');
create type account_purpose as enum ('income', 'spending', 'savings', 'other');

-- ---------- Users ----------
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  created_at timestamptz not null default now()
);

-- ---------- Accounts ----------
-- A user's real bank accounts, each with a role. Example: Opay tagged
-- 'income' (where pay lands), Palmpay tagged 'spending' (day-to-day
-- essentials, tracked against the budget worksheet). is_tracked marks
-- which accounts feed the worksheet totals -- an income-only account
-- can be linked without its balance distorting the spending report.
create table accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  name text not null,                     -- e.g. "Opay", "Palmpay"
  purpose account_purpose not null,
  is_tracked boolean not null default true,
  created_at timestamptz not null default now(),
  unique (user_id, name)
);
create index idx_accounts_user on accounts(user_id);

-- ---------- Categories ----------
-- is_default = true, user_id = null  -> shared worksheet template, visible to everyone
-- user_id set                        -> that user's own custom category
create table categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  name text not null,
  type category_type not null,
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  unique (user_id, name)
);
create index idx_categories_user on categories(user_id);

-- ---------- Statements (uploaded files) ----------
create table statements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  account_id uuid not null references accounts(id) on delete cascade,
  original_filename text not null,
  format statement_format not null,
  status statement_status not null default 'processing',
  uploaded_at timestamptz not null default now(),
  processed_at timestamptz
);
create index idx_statements_user on statements(user_id);
create index idx_statements_account on statements(account_id);

-- ---------- Transactions ----------
create table transactions (
  id uuid primary key default gen_random_uuid(),
  statement_id uuid not null references statements(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  txn_date date not null,
  raw_description text not null,          -- exact bank text, never mutated
  amount numeric(14,2) not null,
  direction txn_direction not null,
  balance_after numeric(14,2),
  category_id uuid references categories(id),
  confidence numeric(4,3),                -- 0.000-1.000, null once user-confirmed
  needs_review boolean not null default true,
  is_internal_transfer boolean not null default false,  -- e.g. Opay -> Palmpay
  linked_transaction_id uuid references transactions(id), -- pairs with the matching leg once both accounts are tracked
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);
create index idx_transactions_user_date on transactions(user_id, txn_date);
create index idx_transactions_statement on transactions(statement_id);
create index idx_transactions_review_queue on transactions(user_id) where needs_review;

-- ---------- Category rules (self-improving cache) ----------
-- Fast lookup layer: description pattern -> category, learned from AI
-- suggestions and user corrections. Checked before calling the AI classifier.
create table category_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  match_key text not null,                -- normalized description fragment (lowercased, trimmed)
  category_id uuid not null references categories(id),
  source rule_source not null,
  times_matched integer not null default 0,
  last_matched_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, match_key)
);
create index idx_rules_user_key on category_rules(user_id, match_key);

-- ---------- Correction audit trail ----------
-- Every time a user changes a category, log it. This is the training
-- signal that updates category_rules and improves future auto-matching.
create table category_corrections (
  id uuid primary key default gen_random_uuid(),
  transaction_id uuid not null references transactions(id) on delete cascade,
  previous_category_id uuid references categories(id),
  new_category_id uuid not null references categories(id),
  corrected_at timestamptz not null default now()
);

-- ---------- Monthly summary (materialized on demand or via scheduled job) ----------
create table monthly_summaries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  month date not null,                    -- first day of month
  total_income numeric(14,2) not null default 0,
  total_fixed_expenses numeric(14,2) not null default 0,
  total_variable_expenses numeric(14,2) not null default 0,
  discretionary_income numeric(14,2) not null default 0,
  generated_at timestamptz not null default now(),
  unique (user_id, month)
);

-- ============================================================
-- Default categories, seeded from the Monthly Budget Worksheet.
-- user_id = null => every user starts with these; they can add more.
-- "Internal Transfer" is included under income per the rule that
-- transfers between a user's own accounts count as income.
-- ============================================================
insert into categories (name, type, is_default) values
  ('Salary / Stipend', 'income', true),
  ('Freelance / Side Income', 'income', true),
  ('Trading Income', 'income', true),
  ('Financial Aid / Support', 'income', true),
  ('Gifts Received', 'income', true),
  ('Internal Transfer', 'income', true),
  ('Other Income', 'income', true),

  ('Regular Savings', 'fixed_expense', true),
  ('Emergency Fund', 'fixed_expense', true),
  ('Rent', 'fixed_expense', true),
  ('Utilities', 'fixed_expense', true),
  ('Airtime & Data', 'fixed_expense', true),
  ('School Fees / Courses', 'fixed_expense', true),
  ('Books & Supplies', 'fixed_expense', true),
  ('Credit Card Payments', 'fixed_expense', true),
  ('Personal Loans / Debts', 'fixed_expense', true),
  ('Bank Charges', 'fixed_expense', true),
  ('Other Fixed Expense', 'fixed_expense', true),

  ('Food & Groceries', 'variable_expense', true),
  ('Household Supplies', 'variable_expense', true),
  ('Transport', 'variable_expense', true),
  ('Medical / Dental / Eye Care', 'variable_expense', true),
  ('Personal Care', 'variable_expense', true),
  ('Tools & Subscriptions', 'variable_expense', true),
  ('Cable TV & Internet', 'variable_expense', true),
  ('Clothes', 'variable_expense', true),
  ('Laundry / Dry Cleaning', 'variable_expense', true),
  ('Snacks & Drinks', 'variable_expense', true),
  ('Entertainment', 'variable_expense', true),
  ('Gifts Given', 'variable_expense', true),
  ('Charity / Contributions', 'variable_expense', true),
  ('Travel', 'variable_expense', true),
  ('Other Variable Expense', 'variable_expense', true)
on conflict do nothing;
