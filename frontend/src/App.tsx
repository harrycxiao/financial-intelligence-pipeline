import {
    BrowserRouter,
    Navigate,
    Route,
    Routes,
    useLocation,
    useNavigate,
} from "react-router-dom";

import {
    Layout,
    NavigationBar,
} from "./components/ui";

import {
    ChatPage,
    CompanyResearchPage,
    HomePage,
    PortfolioResearchPage,
} from "./pages";


/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

type AppPage =
    | "home"
    | "chat"
    | "company"
    | "portfolio";


/* -------------------------------------------------------------------------- */
/* Route Constants                                                            */
/* -------------------------------------------------------------------------- */

const APP_ROUTES = {
    home: "/",
    chat: "/chat",
    company: "/company-research",
    portfolio: "/portfolio-research",
} as const;


/* -------------------------------------------------------------------------- */
/* Route Helpers                                                              */
/* -------------------------------------------------------------------------- */

function getCurrentPage(
    pathname: string,
): AppPage {

    if (pathname.startsWith(APP_ROUTES.chat)) {
        return "chat";
    }

    if (pathname.startsWith(APP_ROUTES.company)) {
        return "company";
    }

    if (pathname.startsWith(APP_ROUTES.portfolio)) {
        return "portfolio";
    }

    return "home";
}


/* -------------------------------------------------------------------------- */
/* Routed Application                                                         */
/* -------------------------------------------------------------------------- */

function RoutedApp() {
    const location = useLocation();
    const navigate = useNavigate();

    const currentPage = getCurrentPage(
        location.pathname,
    );

    function handleNavigate(
        page: AppPage,
    ): void {
        navigate(APP_ROUTES[page]);
    }

    return (
        <Layout>
            <NavigationBar
                currentPage={currentPage}
                onNavigate={handleNavigate}
            />

            <Routes>

                {/* Home */}

                <Route
                    path={APP_ROUTES.home}
                    element={<HomePage />}
                />

                {/* AI Chat */}

                <Route
                    path={APP_ROUTES.chat}
                    element={<ChatPage />}
                />

                {/* Company Research */}

                <Route
                    path={APP_ROUTES.company}
                    element={
                        <CompanyResearchPage />
                    }
                />

                {/* Portfolio Research */}

                <Route
                    path={APP_ROUTES.portfolio}
                    element={
                        <PortfolioResearchPage />
                    }
                />

                {/* Unknown Route */}

                <Route
                    path="*"
                    element={
                        <Navigate
                            to={APP_ROUTES.home}
                            replace
                        />
                    }
                />

            </Routes>
        </Layout>
    );
}


/* -------------------------------------------------------------------------- */
/* Application                                                                */
/* -------------------------------------------------------------------------- */

export default function App() {
    return (
        <BrowserRouter>
            <RoutedApp />
        </BrowserRouter>
    );
}