import { useNavigate } from 'react-router-dom';

interface ProjectLinkProps {
  projectId: number | string;
  name: string;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * Reusable component to render a clickable project name
 * that navigates to the project detail page.
 */
export default function ProjectLink({ projectId, name, style, className }: ProjectLinkProps) {
  const navigate = useNavigate();

  return (
    <span
      className={className}
      onClick={(e) => { e.stopPropagation(); navigate(`/projects/${projectId}`); }}
      style={{
        cursor: 'pointer',
        color: 'var(--cv-accent)',
        fontWeight: 600,
        textDecoration: 'none',
        transition: 'opacity 0.15s',
        ...style,
      }}
      onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
      onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
      title={`Ver detalhes: ${name}`}
    >
      {name}
    </span>
  );
}
