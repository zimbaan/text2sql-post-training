# NL-SQL Agent: frontend

React + TypeScript + Vite UI for the NL→SQL backend in `../backend`: connect a database, ask questions in plain
English, review the generated SQL, run it, chart results, explore table relationships, and export CSV.

## Run

```bash
npm install
cp .env.example .env    # VITE_API_BASE_URL=http://localhost:8000
npm run dev             # http://localhost:8080
```

`npm run build` writes a production build to `dist/`.

## Model picker

The model picker in the navbar lists the backend's models. The post-trained text-to-SQL model
(`text2sql-qwen-0.5b-dpo`, marked "fine-tuned") appears first when the backend has it installed. The chosen
model is sent with every query, and the SQL preview shows which model produced the SQL.

## Stack

React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui (Radix), TanStack Query, React Router, Recharts, and
React Flow for the table-relationship graph.
