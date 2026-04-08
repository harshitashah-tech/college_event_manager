-- ============================================================
-- schema.sql
-- College Event Management System – Full Database Schema
-- Target: Supabase (PostgreSQL)
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. USERS
-- Extends Supabase auth.users with app-level profile data.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.users (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL DEFAULT 'student'
                        CHECK (role IN ('student', 'coordinator', 'admin')),
    department      TEXT,
    year_of_study   INT,
    phone           TEXT,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. CLUBS
-- Managed by coordinators, approved by admin.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.clubs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    category        TEXT,
    coordinator_id  UUID REFERENCES public.users(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
    logo_url        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. CLUB MEMBERS
-- Students who have joined / applied to clubs.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.club_members (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id     UUID NOT NULL REFERENCES public.clubs(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (club_id, user_id)
);

-- ============================================================
-- 4. EVENTS
-- Created by coordinators, approved by admin.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,
    club_id         UUID REFERENCES public.clubs(id) ON DELETE SET NULL,
    coordinator_id  UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_date      TIMESTAMPTZ NOT NULL,
    registration_deadline TIMESTAMPTZ,
    venue           TEXT,
    max_participants INT DEFAULT 0,    -- 0 = unlimited
    is_paid         BOOLEAN NOT NULL DEFAULT FALSE,
    ticket_price    NUMERIC(10,2) DEFAULT 0.00,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
    banner_url      TEXT,
    tags            TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. REGISTRATIONS
-- Student registrations for events.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.registrations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cancelled       BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at    TIMESTAMPTZ,
    UNIQUE (event_id, user_id)
);

-- ============================================================
-- 6. PAYMENTS
-- Simulated payment records (no real gateway).
-- ============================================================
CREATE TABLE IF NOT EXISTS public.payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    registration_id UUID NOT NULL REFERENCES public.registrations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    amount          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'paid', 'failed')),
    transaction_ref TEXT UNIQUE,
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. CERTIFICATES
-- Issued per event per user; file stored in Supabase Storage.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.certificates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    cert_type       TEXT NOT NULL DEFAULT 'participation'
                        CHECK (cert_type IN ('participation', 'winner', 'organizer')),
    file_url        TEXT,
    issued_by       UUID REFERENCES public.users(id),
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, user_id, cert_type)
);

-- ============================================================
-- 8. NOTIFICATIONS
-- System + admin announcements stored per user.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'info'
                    CHECK (type IN ('info', 'success', 'warning', 'error')),
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    related_event_id UUID REFERENCES public.events(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES  (improve query performance)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_events_status       ON public.events(status);
CREATE INDEX IF NOT EXISTS idx_events_date         ON public.events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_category     ON public.events(category);
CREATE INDEX IF NOT EXISTS idx_registrations_user  ON public.registrations(user_id);
CREATE INDEX IF NOT EXISTS idx_registrations_event ON public.registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user  ON public.notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_payments_user       ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_club_members_user   ON public.club_members(user_id);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS) – basic policies
-- ============================================================
ALTER TABLE public.users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clubs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.club_members   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registrations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.certificates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications  ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read all approved events
CREATE POLICY "Public events visible"
    ON public.events FOR SELECT
    USING (status = 'approved');

-- Allow users to read their own data
CREATE POLICY "Users read own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- All authenticated users can insert their own profile
CREATE POLICY "Users insert own profile"
    ON public.users FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Registrations: users manage their own
CREATE POLICY "Users manage own registrations"
    ON public.registrations FOR ALL
    USING (auth.uid() = user_id);

-- Payments: users see their own
CREATE POLICY "Users see own payments"
    ON public.payments FOR ALL
    USING (auth.uid() = user_id);

-- Certificates: users see their own
CREATE POLICY "Users see own certificates"
    ON public.certificates FOR SELECT
    USING (auth.uid() = user_id);

-- Notifications: users see their own
CREATE POLICY "Users see own notifications"
    ON public.notifications FOR ALL
    USING (auth.uid() = user_id);

-- Club members: see own memberships
CREATE POLICY "Users see own club memberships"
    ON public.club_members FOR ALL
    USING (auth.uid() = user_id);

-- Clubs: anyone can read approved clubs
CREATE POLICY "Public clubs visible"
    ON public.clubs FOR SELECT
    USING (status = 'approved');

-- ============================================================
-- HELPER: auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_clubs_updated_at
    BEFORE UPDATE ON public.clubs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON public.events
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
