--
-- PostgreSQL database dump
--

\restrict fqogGcfWmYVwUWmNBBJnImZiG5Nfjvo9rTupcM1tflgplVOoRi5jaa6z5d2XMMg

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: feriados; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feriados (id, data, uf, cidade, ds_feriado, tipo, criado_em) FROM stdin;
1	2024-01-01	\N	\N	Confraternização Universal	nacional	2026-09-20 21:32:48.203639
2	2024-03-09	SC	Joinville	Aniversário de Joinville	municipal	2026-09-20 21:32:48.203639
3	2024-03-29	\N	\N	Paixão de Cristo	nacional	2026-09-20 21:32:48.203639
4	2024-04-21	\N	\N	Tiradentes	nacional	2026-09-20 21:32:48.203639
5	2024-05-01	\N	\N	Dia do Trabalho	nacional	2026-09-20 21:32:48.203639
6	2024-09-07	\N	\N	Independência do Brasil	nacional	2026-09-20 21:32:48.203639
7	2024-10-12	\N	\N	Nossa Senhora Aparecida	nacional	2026-09-20 21:32:48.203639
8	2024-11-02	\N	\N	Finados	nacional	2026-09-20 21:32:48.203639
9	2024-11-15	\N	\N	Proclamação da República	nacional	2026-09-20 21:32:48.203639
10	2024-11-20	\N	\N	Dia da Consciência Negra	nacional	2026-09-20 21:32:48.203639
11	2024-12-25	\N	\N	Natal	nacional	2026-09-20 21:32:48.203639
12	2025-01-01	\N	\N	Confraternização Universal	nacional	2026-09-20 21:32:48.507617
13	2025-03-09	SC	Joinville	Aniversário de Joinville	municipal	2026-09-20 21:32:48.507617
14	2025-04-18	\N	\N	Paixão de Cristo	nacional	2026-09-20 21:32:48.507617
15	2025-04-21	\N	\N	Tiradentes	nacional	2026-09-20 21:32:48.507617
16	2025-05-01	\N	\N	Dia do Trabalho	nacional	2026-09-20 21:32:48.507617
17	2025-09-07	\N	\N	Independência do Brasil	nacional	2026-09-20 21:32:48.507617
18	2025-10-12	\N	\N	Nossa Senhora Aparecida	nacional	2026-09-20 21:32:48.507617
19	2025-11-02	\N	\N	Finados	nacional	2026-09-20 21:32:48.507617
20	2025-11-15	\N	\N	Proclamação da República	nacional	2026-09-20 21:32:48.507617
21	2025-11-20	\N	\N	Dia da Consciência Negra	nacional	2026-09-20 21:32:48.507617
22	2025-12-25	\N	\N	Natal	nacional	2026-09-20 21:32:48.507617
23	2026-01-01	\N	\N	Confraternização Universal	nacional	2026-09-20 21:32:48.726269
24	2026-03-09	SC	Joinville	Aniversário de Joinville	municipal	2026-09-20 21:32:48.726269
25	2026-04-03	\N	\N	Paixão de Cristo	nacional	2026-09-20 21:32:48.726269
26	2026-04-21	\N	\N	Tiradentes	nacional	2026-09-20 21:32:48.726269
27	2026-05-01	\N	\N	Dia do Trabalho	nacional	2026-09-20 21:32:48.726269
28	2026-08-16	SC	\N	Dia do Estado de Santa Catarina (Data Magna)	estadual	2026-09-20 21:32:48.726269
29	2026-09-07	\N	\N	Independência do Brasil	nacional	2026-09-20 21:32:48.726269
30	2026-10-12	\N	\N	Nossa Senhora Aparecida	nacional	2026-09-20 21:32:48.726269
31	2026-11-02	\N	\N	Finados	nacional	2026-09-20 21:32:48.726269
32	2026-11-15	\N	\N	Proclamação da República	nacional	2026-09-20 21:32:48.726269
33	2026-11-20	\N	\N	Dia da Consciência Negra	nacional	2026-09-20 21:32:48.726269
34	2026-12-25	\N	\N	Natal	nacional	2026-09-20 21:32:48.726269
35	2027-01-01	\N	\N	Confraternização Universal	nacional	2026-09-20 21:32:48.931453
36	2027-03-09	SC	Joinville	Aniversário de Joinville	municipal	2026-09-20 21:32:48.931453
37	2027-03-26	\N	\N	Paixão de Cristo	nacional	2026-09-20 21:32:48.931453
38	2027-04-21	\N	\N	Tiradentes	nacional	2026-09-20 21:32:48.931453
39	2027-05-01	\N	\N	Dia do Trabalho	nacional	2026-09-20 21:32:48.931453
40	2027-08-11	SC	\N	Criação da capitania	estadual	2026-09-20 21:32:48.931453
41	2027-09-07	\N	\N	Independência do Brasil	nacional	2026-09-20 21:32:48.931453
42	2027-10-12	\N	\N	Nossa Senhora Aparecida	nacional	2026-09-20 21:32:48.931453
43	2027-11-02	\N	\N	Finados	nacional	2026-09-20 21:32:48.931453
44	2027-11-15	\N	\N	Proclamação da República	nacional	2026-09-20 21:32:48.931453
45	2027-11-20	\N	\N	Dia da Consciência Negra	nacional	2026-09-20 21:32:48.931453
46	2027-12-25	\N	\N	Natal	nacional	2026-09-20 21:32:48.931453
47	2024-03-29	PR	Curitiba	Aniversário de Curitiba	municipal	2026-09-20 21:32:49.160934
48	2024-12-19	PR	\N	Emancipação do Paraná	estadual	2026-09-20 21:32:49.160934
49	2025-03-29	PR	Curitiba	Aniversário de Curitiba	municipal	2026-09-20 21:32:49.361322
50	2025-12-19	PR	\N	Emancipação do Paraná	estadual	2026-09-20 21:32:49.361322
51	2026-06-04	PR	Curitiba	Corpus Christi	municipal	2026-09-20 21:32:49.56673
52	2027-03-29	PR	Curitiba	Aniversário de Curitiba	municipal	2026-09-20 21:32:49.773673
53	2027-09-08	PR	Curitiba	Nossa Senhora da Luz dos Pinhais	municipal	2026-09-20 21:32:49.773673
54	2027-12-19	PR	\N	Emancipação do Paraná	estadual	2026-09-20 21:32:49.773673
55	2024-01-25	SP	São Paulo	Aniversário de São Paulo	municipal	2026-09-20 21:32:49.97885
56	2024-07-09	SP	\N	Revolução Constitucionalista de 1932	estadual	2026-09-20 21:32:49.97885
57	2025-01-25	SP	São Paulo	Aniversário de São Paulo	municipal	2026-09-20 21:32:50.179496
58	2025-07-09	SP	\N	Revolução Constitucionalista de 1932	estadual	2026-09-20 21:32:50.179496
59	2026-07-09	SP	\N	Revolução Constitucionalista de 1932	estadual	2026-09-20 21:32:50.384234
60	2027-01-25	SP	São Paulo	Aniversário de São Paulo	municipal	2026-09-20 21:32:50.582998
61	2027-05-27	SP	São Paulo	Corpus Christi	municipal	2026-09-20 21:32:50.582998
62	2027-07-09	SP	\N	Revolução Constitucionalista de 1932	estadual	2026-09-20 21:32:50.582998
63	2027-11-20	SP	São Paulo	Consciência Negra	municipal	2026-09-20 21:32:50.582998
\.


--
-- Name: feriados_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.feriados_id_seq', 63, true);


--
-- PostgreSQL database dump complete
--

\unrestrict fqogGcfWmYVwUWmNBBJnImZiG5Nfjvo9rTupcM1tflgplVOoRi5jaa6z5d2XMMg

