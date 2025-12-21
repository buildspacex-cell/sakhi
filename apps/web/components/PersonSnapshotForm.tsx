'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useState } from 'react';

type Props = {
  initialPersonId: string;
};

export function PersonSnapshotForm({ initialPersonId }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(initialPersonId);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextId = value.trim() || initialPersonId;
    const params = new URLSearchParams(searchParams?.toString() ?? '');
    params.set('person_id', nextId);
    const nextUrl = `${pathname}?${params.toString()}`;
    router.push(nextUrl as any);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <label htmlFor="person-id-input" style={{ fontWeight: 500 }}>
        Person ID
      </label>
      <input
        id="person-id-input"
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        style={{
          flex: '1 1 320px',
          minWidth: '220px',
          padding: '0.55rem 0.85rem',
          borderRadius: '12px',
          border: '1px solid rgba(120,107,96,0.4)',
          fontSize: '0.95rem',
        }}
        placeholder="565bdb63-124b-4692-a039-846fddceff90"
      />
      <button
        type="submit"
        style={{
          padding: '0.55rem 1.25rem',
          borderRadius: '999px',
          border: 'none',
          background: 'linear-gradient(135deg,#FB7185,#F97316)',
          color: '#fff',
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Load Snapshot
      </button>
    </form>
  );
}

export default PersonSnapshotForm;
